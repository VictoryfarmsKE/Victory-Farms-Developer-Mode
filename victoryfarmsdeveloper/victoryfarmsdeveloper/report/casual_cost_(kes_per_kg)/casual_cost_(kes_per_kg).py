# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, get_last_day


def execute(filters=None):
	filters = filters or {}
	from_date, to_date = compute_date_range(filters)

	casual_costs = get_casual_costs(from_date, to_date)
	harvest_qty = get_harvest_qty(from_date, to_date)

	cost_per_kg = (casual_costs / harvest_qty) if harvest_qty else 0
	score = _score(cost_per_kg)

	columns = get_columns()
	data = [
		{
			"casual_costs_kes": round(casual_costs, 2),
			"total_harvest_kg": round(harvest_qty, 3),
			"casual_costs_per_kg": round(cost_per_kg, 3),
			"score": score,
		}
	]

	return columns, data


def get_columns():
	return [
		{
			"label": "Casual costs (KES)",
			"fieldname": "casual_costs_kes",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": "Total Harvest (KG)",
			"fieldname": "total_harvest_kg",
			"fieldtype": "Float",
			"width": 160,
		},
		{
			"label": "Casual Costs/Kg",
			"fieldname": "casual_costs_per_kg",
			"fieldtype": "Currency",
			"options": "KES",
			"width": 160,
		},
		{
			"label": "Score (1-5)",
			"fieldname": "score",
			"fieldtype": "Int",
			"width": 120,
		},
	]


def compute_date_range(filters):
	"""
	Compute from_date and to_date based on mandatory filters
	"""
	month = (filters.get("month") or "").strip()
	fiscal_year_name = (filters.get("year") or "").strip()

	if not month or not fiscal_year_name:
		raise frappe.ValidationError("Both Month and Fiscal Year are required.")

	month_num = month_name_to_number(month)
	if not month_num:
		raise frappe.ValidationError(f"Invalid month: {month}")

	fy = frappe.get_doc("Fiscal Year", fiscal_year_name)
	fy_start = getdate(fy.year_start_date)
	fy_end = getdate(fy.year_end_date)

	year = fy_start.year if month_num >= fy_start.month else fy_end.year
	from_date = getdate(f"{year}-{month_num:02d}-01")
	to_date = get_last_day(from_date)


	if not (fy_start <= from_date <= fy_end):
		raise frappe.ValidationError(
			f"Selected month '{month}' does not fall within Fiscal Year '{fiscal_year_name}'."
		)

	return from_date, to_date

def month_name_to_number(name):
	name = (name or "").strip().lower()
	months = {
		"january": 1,
		"february": 2,
		"march": 3,
		"april": 4,
		"may": 5,
		"june": 6,
		"july": 7,
		"august": 8,
		"september": 9,
		"october": 10,
		"november": 11,
		"december": 12,
	}
	return months.get(name)


def get_casual_costs(from_date, to_date):
	"""Sum of grand_total from Purchase Orders for supplier and department within date range."""
	supplier = "VF Farm Casual Wages"
	custom_department = "Processing - VFL"
	return (
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(grand_total), 0)
			FROM `tabPurchase Order`
			WHERE docstatus = 1
			  AND supplier = %s
			  AND custom_department = %s
			  AND transaction_date BETWEEN %s AND %s
			""",
			(supplier, custom_department, from_date, to_date),
		)[0][0]
		or 0
	)


def get_harvest_qty(from_date, to_date):
	"""Sum of qty from Stock Entry Details for Harvested Round Fish within date range."""
	stock_entry_type = "Harvesting of Fish"
	item_code = "Harvested Round Fish"
	return (
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(sed.qty), 0)
			FROM `tabStock Entry` se
			JOIN `tabStock Entry Detail` sed ON sed.parent = se.name AND sed.parenttype = 'Stock Entry'
			WHERE se.docstatus = 1
			  AND se.stock_entry_type = %s
			  AND sed.item_code = %s
			  AND se.posting_date BETWEEN %s AND %s
			""",
			(stock_entry_type, item_code, from_date, to_date),
		)[0][0]
		or 0
	)


def _score(value):
	"""Map cost/kg to score based on provided criteria.

	Criteria:
	- value <= 1.5 -> 5
	- 1.5 < value <= 2 -> 4
	- 2 < value <= 2.5 -> 3
	- 2.5 < value < 4 -> 2
	- value >= 4 -> 1
	"""
	if value <= 1.5:
		return 5
	if value <= 2:
		return 4
	if value <= 2.5:
		return 3
	if value < 4:
		return 2
	return 1
