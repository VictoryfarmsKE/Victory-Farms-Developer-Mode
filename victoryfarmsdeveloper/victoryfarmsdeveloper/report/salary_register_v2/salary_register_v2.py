# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt

import erpnext

salary_slip = frappe.qb.DocType("Salary Slip")
salary_detail = frappe.qb.DocType("Salary Detail")
salary_component = frappe.qb.DocType("Salary Component")


def execute(filters=None):
	if not filters:
		filters = {}

	currency = None
	if filters.get("currency"):
		currency = filters.get("currency")
	company_currency = erpnext.get_company_currency(filters.get("company"))

	salary_slips = get_salary_slips(filters, company_currency)
	if not salary_slips:
		return [], []

	earning_types, ded_types = get_earning_and_deduction_types(salary_slips)
	columns = get_columns(earning_types, ded_types)

	ss_earning_map = get_salary_slip_details(salary_slips, currency, company_currency, "earnings")
	ss_ded_map = get_salary_slip_details(salary_slips, currency, company_currency, "deductions")

	doj_map = get_employee_doj_map()
 
	# Get employee payroll cost center map
	payroll_cost_center_map = get_employee_payroll_cost_center_map()
 
	# Get employee grade map
	employee_grade_map = get_employee_grade_map()

	data = []
	for ss in salary_slips:
		row = {
			"salary_slip_id": ss.name,
			"employee": ss.employee,
			"employee_name": ss.employee_name,
			"grade": employee_grade_map.get(ss.employee),
			"data_of_joining": doj_map.get(ss.employee),
			"payroll_cost_center": payroll_cost_center_map.get(ss.employee),
			"branch": ss.branch,
			"department": ss.department,
			"designation": ss.designation,
			"company": ss.company,
			"start_date": ss.start_date,
			"end_date": ss.end_date,
			"leave_without_pay": ss.leave_without_pay,
			"payment_days": ss.payment_days,
			"regular_working_hours": ss.regular_working_hours,
			"overtime_hours": ss.overtime_hours,
			"holiday_hourss": ss.holiday_hours,
			"hourly_rate": ss.hourly_rate,
			"currency": currency or company_currency,
			"total_loan_repayment": ss.total_loan_repayment,
			"net_pay_bonus": ss.custom_net_pay_excluding_bonus,
		}

		update_column_width(ss, columns)

		for e in earning_types:
			value = ss_earning_map.get(ss.name, {}).get(e, 0)
			row.update({frappe.scrub(e): value if value is not None else 0})

		for d in ded_types:
			value = ss_ded_map.get(ss.name, {}).get(d, 0)
			row.update({frappe.scrub(d): value if value is not None else 0})
    
		if currency == company_currency:
			row.update(
				{
					"gross_pay": flt(ss.gross_pay) * flt(ss.exchange_rate),
					"total_deduction": flt(ss.total_deduction) * flt(ss.exchange_rate),
					"net_pay": flt(ss.net_pay) * flt(ss.exchange_rate),
					"net_pay_bonus": flt(ss.custom_net_pay_excluding_bonus) * flt(ss.exchange_rate) if ss.custom_net_pay_excluding_bonus else 0,
     
				}
			)

		else:
			row.update(
				{"gross_pay": ss.gross_pay, "total_deduction": ss.total_deduction, "net_pay": ss.net_pay}
			)

		data.append(row)

	return columns, data


def get_earning_and_deduction_types(salary_slips):
	salary_component_and_type = {_("Earning"): [], _("Deduction"): []}

	for salary_component in get_salary_components(salary_slips):
		component_type = get_salary_component_type(salary_component)
		salary_component_and_type[_(component_type)].append(salary_component)
  
		# Custom order for earnings
		# preferred_earning_order = ["Basic Pay", "Basic Salary", "OT hours", "Holiday Hours", "Overtime 2.0", "Overtime 1.5", "Arrear", "Bonus Department", "Bonus Department (Quarterly)", "Bonus Department (Annual)", "Bonus Individual", "Bonus Individual (Quarterly)", "Bonus Individual (Annual)", "Bonus Company (Annual)", "Commercial Commission", "Commercial Holiday Pay", "Education Allowance", "General Allowance", "House Rent", "Leave Encashment", "Net Arrears", "Notice Allowance", "OP Arrears", "Taxable Income", "Transport Allowance", "Unpaid Leave"]
		preferred_earning_order = ["Basic Pay", "Basic Salary", "OT hours", "Holiday Hours", "Arrear", "Bonus Department", "Bonus Department (Quarterly)", "Bonus Department (Annual)", "Bonus Individual", "Bonus Individual (Quarterly)", "Bonus Individual (Annual)", "Bonus Company (Annual)", "Commercial Commission", "Commercial Holiday Pay", "Education Allowance", "General Allowance", "Urban Allowance", "Ex-Gratia", "House Rent", "Leave Encashment", "Net Arrears", "Notice Allowance", "OP Arrears", "Taxable Income", "Transport Allowance", "Unpaid Leave"]
		ordered_earnings = preferred_earning_order
  		# earnings = salary_component_and_type[_("Earning")]
		# ordered_earnings = [e for e in preferred_earning_order if e in earnings]
		# ordered_earnings += [e for e in earnings if e not in preferred_earning_order]
  
		# Custom order for deductions
		preferred_deduction_order = ["Salary Advance","Notice Pay Deduction", "Social Health Insurance Fund", "Employee Housing Levy", "Employer Housing Levy", "Employee NSSF T1", "Employee NSSF T2", "Employer NSSF T1", "Employer NSSF T2", "Voluntary NSSF", "HELB", "Gross Insurance Relief", "Gross PAYE", "Insurance", "Insurance 2", "Insurance Relief", "Bereavement Fund", "COTU Fees", "KLDTD Union", "Max Insurance Relief", "Mortgage Interest", "Personal Relief", "PAYE", "Sacco Deposits", "Sacco Loan (Deduction)", "Sacco Registration Fee", "Lost Items", "Accidents Repair Deduction", "VF Store"]
		ordered_deductions = preferred_deduction_order
		# deductions = salary_component_and_type[_("Deduction")]
		# ordered_deductions = [d for d in preferred_deduction_order if d in deductions]
		# ordered_deductions += [d for d in deductions if d not in preferred_deduction_order]
	return ordered_earnings, ordered_deductions

	# return sorted(salary_component_and_type[_("Earning")]), sorted(salary_component_and_type[_("Deduction")])


def update_column_width(ss, columns):
	if ss.branch is not None:
		columns[3].update({"width": 120})
	if ss.department is not None:
		columns[4].update({"width": 120})
	if ss.designation is not None:
		columns[5].update({"width": 120})
	if ss.leave_without_pay is not None:
		columns[9].update({"width": 120})


def get_columns(earning_types, ded_types):
	columns = [
		{
			"label": _("Salary Slip ID"),
			"fieldname": "salary_slip_id",
			"fieldtype": "Link",
			"options": "Salary Slip",
			"width": 150,
		},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Grade"),
			"fieldname": "grade",	
			"fieldtype": "Link",
			"options": "Employee Grade",
			"width": 120,
		},
		{
			"label": _("Date of Joining"),
			"fieldname": "data_of_joining",
			"fieldtype": "Date",
			"width": 80,
		},
		# {
		# 	"label": _("Branch"),
		# 	"fieldname": "branch",
		# 	"fieldtype": "Link",
		# 	"options": "Branch",
		# 	"width": -1,
		# },
		{
			"label": _("Department"),
			"fieldname": "payroll_cost_center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": -1,
		},
		{
			"label": _("Designation"),
			"fieldname": "designation",
			"fieldtype": "Link",
			"options": "Designation",
			"width": 120,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
		{
			"label": _("Start Date"),
			"fieldname": "start_date",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("End Date"),
			"fieldname": "end_date",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Leave Without Pay"),
			"fieldname": "leave_without_pay",
			"fieldtype": "Float",
			"width": 50,
		},
		{
			"label": _("Payment Days"),
			"fieldname": "payment_days",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Regular Working Hours (hr)"),
			"fieldname": "regular_working_hours",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Overtime Hours (hr)"),
			"fieldname": "overtime_hours",
			"fieldtype": "Float",
			"width": 120,				
		},
		{
			"label": _("Holiday Hours (hr)"),
			"fieldname": "holiday_hourss",
			"fieldtype": "Float",									
			"width": 120,
		},
		{
			"label": _("Hourly Rate"),
			"fieldname": "hourly_rate",
			"fieldtype": "Currency",									
			"width": 120,
		},
				

	]

	for earning in earning_types:
		if earning == "OT hours":
			earning = "OT hours"
		elif earning == "Holiday Hours":
			earning = "Holiday Hours"
		# elif earning == "Overtime 1.5":
		# 	earning = "Overtime 1.5 (KES)"
		# elif earning == "Overtime 2.0":
		# 	earning = "Overtime 2.0 (KES)"
		columns.append(
			{
				"label": earning,
				"fieldname": frappe.scrub(earning),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		)

	columns.append(
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		}
	)

	for deduction in ded_types:
		columns.append(
			{
				"label": deduction,
				"fieldname": frappe.scrub(deduction),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		)

	columns.extend(
		[
			{
				"label": _("Loan Repayment"),
				"fieldname": "total_loan_repayment",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Total Deduction"),
				"fieldname": "total_deduction",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Net Pay"),
				"fieldname": "net_pay",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
{
				"label": _("Net Pay (Bonus"),
				"fieldname": "net_pay_bonus",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Currency"),
				"fieldtype": "Data",
				"fieldname": "currency",
				"options": "Currency",
				"hidden": 1,
			},
		]
	)
	return columns


def get_salary_components(salary_slips):
	return (
		frappe.qb.from_(salary_detail)
		.where((salary_detail.amount != 0) & (salary_detail.parent.isin([d.name for d in salary_slips])))
		.select(salary_detail.salary_component)
		.distinct()
	).run(pluck=True)


def get_salary_component_type(salary_component):
	return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


def get_salary_slips(filters, company_currency):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	query = frappe.qb.from_(salary_slip).select(salary_slip.star)

	if filters.get("docstatus"):
		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])

	if filters.get("from_date"):
		query = query.where(salary_slip.start_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(salary_slip.end_date <= filters.get("to_date"))

	if filters.get("company"):
		query = query.where(salary_slip.company == filters.get("company"))

	if filters.get("employee"):
		query = query.where(salary_slip.employee == filters.get("employee"))

	if filters.get("currency") and filters.get("currency") != company_currency:
		query = query.where(salary_slip.currency == filters.get("currency"))

	salary_slips = query.run(as_dict=1)

	return salary_slips or []


def get_employee_doj_map():
	employee = frappe.qb.DocType("Employee")

	result = (frappe.qb.from_(employee).select(employee.name, employee.date_of_joining)).run()

	return frappe._dict(result)

#get emmployee grade map
def get_employee_grade_map():	
	employee = frappe.qb.DocType("Employee")

	result = (frappe.qb.from_(employee).select(employee.name, employee.grade)).run()

	return frappe._dict(result)

#get employee payroll cost center map
def get_employee_payroll_cost_center_map():
	employee = frappe.qb.DocType("Employee")

	result = (frappe.qb.from_(employee).select(employee.name, employee.payroll_cost_center)).run()

	return frappe._dict(result)

def get_salary_slip_details(salary_slips, currency, company_currency, component_type):
	salary_slips = [ss.name for ss in salary_slips]

	result = (
		frappe.qb.from_(salary_slip)
		.join(salary_detail)
		.on(salary_slip.name == salary_detail.parent)
		.where((salary_detail.parent.isin(salary_slips)) & (salary_detail.parentfield == component_type))
		.select(
			salary_detail.parent,
			salary_detail.salary_component,
			salary_detail.amount,
			salary_slip.exchange_rate,
		)
	).run(as_dict=1)

	ss_map = {}

	for d in result:
		ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
		if currency == company_currency:
			ss_map[d.parent][d.salary_component] += flt(d.amount) * flt(
				d.exchange_rate if d.exchange_rate else 1
			)
		else:
			ss_map[d.parent][d.salary_component] += flt(d.amount)

	return ss_map