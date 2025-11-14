# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	"""Generate bank payment template.

	Expected filters:
	- from_date, to_date (required)
	- salary_currency (optional, defaults KES)
	- GET earning & deduction 
	"""
	if not filters:
		filters = {}
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if not from_date or not to_date:
		frappe.throw(_("Please set From Date and To Date filters"))
	if from_date > to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	show_components = frappe.utils.cint(filters.get("show_components"))

	# Base columns
	columns = get_columns()

	# Fetch base payment rows (grouped per employee)
	rows = get_data(filters)

	if not rows:
		return columns, []

	# Enrich with earnings & deductions breakdown
	earnings_map, deductions_map, earning_components, deduction_components = get_component_maps(filters)

	# Mandatory bonus earning components to always display
	mandatory_bonus_components = [
		"Bonus Department",
		"Bonus Department (Quarterly)",
		"Bonus Department (Annual)",
		"Bonus Individual",
		"Bonus Individual (Quarterly)",
		"Bonus Individual (Annual)",
		"Bonus Company (Annual)",
	]

	# Add summary columns
	# columns.extend([
	# 	{"fieldname": "total_earnings", "label": _("Total Earnings"), "fieldtype": "Currency", "width": 120},
	# 	{"fieldname": "total_deductions", "label": _("Total Deductions"), "fieldtype": "Currency", "width": 120},
	# ])

	# Add per-component columns
	if show_components:
		for comp in earning_components:
			fieldname = frappe.scrub(comp)
			if not any(c.get("fieldname") == fieldname for c in columns):
				columns.append({
					"fieldname": fieldname,
					"label": comp,
					"fieldtype": "Currency",
					"width": 120,
				})
		for comp in deduction_components:
			fieldname = frappe.scrub(comp)
			if not any(c.get("fieldname") == fieldname for c in columns):
				columns.append({
					"fieldname": fieldname,
					"label": comp,
					"fieldtype": "Currency",
					"width": 120,
				})

	# Always append mandatory bonus columns (avoiding duplicates)
	# for comp in mandatory_bonus_components:
	# 	fieldname = frappe.scrub(comp)
	# 	if not any(c.get("fieldname") == fieldname for c in columns):
	# 		columns.append({
	# 			"fieldname": fieldname,
	# 			"label": comp,
	# 			"fieldtype": "Currency",
	# 			"width": 120,
	# 		})

	for r in rows:
		emp = r.get("beneficiary_name")
		# Maps keyed by employee name from salary slips
		emp_earnings = earnings_map.get(emp, {})
		emp_deductions = deductions_map.get(emp, {})
		# Subtract selected bonus earnings from net pay to derive payment amount
		bonus_total = sum(emp_earnings.get(comp, 0) for comp in mandatory_bonus_components)
		r["payment_amount"] = (r.get("payment_amount") or 0) - bonus_total
		# Totals
		r["total_earnings"] = sum(emp_earnings.values())
		r["total_deductions"] = sum(emp_deductions.values())
		if show_components:
			for comp, amt in emp_earnings.items():
				r[frappe.scrub(comp)] = amt
			for comp, amt in emp_deductions.items():
				r[frappe.scrub(comp)] = amt
		# Mandatory bonus components (show_components even when = 0)
		for comp in mandatory_bonus_components:
			fieldname = frappe.scrub(comp)
			if fieldname not in r:
				r[fieldname] = emp_earnings.get(comp, 0)

	return columns, rows


def get_columns():
	return [
		{"fieldname": "beneficiary_name", "label": _("Beneficiary Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "transaction_currency", "label": _("Currency"), "fieldtype": "Link", "options": "Currency", "width": 90},
		{"fieldname": "payment_amount", "label": _("Net Pay"), "fieldtype": "Float", "width": 120},
	]


def get_data(filters):
	salary_currency = filters.get("salary_currency", "USD")

	params = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"salary_currency": salary_currency,
	}

	query = """
	SELECT
		MAX(ss.employee_name) AS beneficiary_name,
		emp.salary_currency AS transaction_currency,
		SUM(ss.net_pay) AS payment_amount
	FROM `tabSalary Slip` ss
	INNER JOIN `tabEmployee` emp ON emp.name = ss.employee
	WHERE ss.docstatus = 1
		AND emp.salary_currency = %(salary_currency)s
		AND ss.posting_date BETWEEN %(from_date)s AND %(to_date)s
	GROUP BY emp.name, emp.salary_currency
	ORDER BY emp.name
	"""

	return frappe.db.sql(query, params, as_dict=True)


def get_component_maps(filters):
	"""Return earning and deduction component maps per employee along with ordered component name lists."""
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	salary_currency = filters.get("salary_currency", "KES")

	# Get Salary Slips =
	slip_rows = frappe.db.sql(
		"""
		SELECT ss.name, ss.employee, ss.employee_name
		FROM `tabSalary Slip` ss
		JOIN `tabEmployee` emp ON emp.name = ss.employee
		WHERE ss.docstatus = 1
			AND ss.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND emp.salary_currency = %(salary_currency)s
		""",
		{"from_date": from_date, "to_date": to_date, "salary_currency": salary_currency},
		as_dict=True,
	)

	if not slip_rows:
		return {}, {}, [], []

	slip_names = [r["name"] for r in slip_rows]
	employee_name_map = {r["name"]: r["employee_name"] for r in slip_rows}

	def fetch_components(parentfield):
		return frappe.db.sql(
			"""
			SELECT ss.employee_name AS employee_name,
			       sd.salary_component AS component,
			       SUM(sd.amount) AS amount
			FROM `tabSalary Detail` sd
			JOIN `tabSalary Slip` ss ON sd.parent = ss.name
			WHERE sd.parentfield = %(parentfield)s
			  AND sd.amount != 0
			  AND sd.parent IN %(parents)s
			GROUP BY ss.employee_name, sd.salary_component
			""",
			{"parentfield": parentfield, "parents": tuple(slip_names)},
			as_dict=True,
		)

	earning_rows = fetch_components("earnings")
	deduction_rows = fetch_components("deductions")

	earnings_map = {}
	deductions_map = {}
	for er in earning_rows:
		earnings_map.setdefault(er["employee_name"], {})[er["component"]] = er["amount"]
	for dr in deduction_rows:
		deductions_map.setdefault(dr["employee_name"], {})[dr["component"]] = dr["amount"]

	# Order components (basic first for earnings if exists)
	earning_components = sorted({r["component"] for r in earning_rows})
	deduction_components = sorted({r["component"] for r in deduction_rows})
	if "Basic Salary" in earning_components:
		earning_components.remove("Basic Salary")
		earning_components = ["Basic Salary"] + earning_components

	return earnings_map, deductions_map, earning_components, deduction_components
