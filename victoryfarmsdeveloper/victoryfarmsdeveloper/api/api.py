import frappe
from frappe.utils import getdate, get_last_day


@frappe.whitelist()
def fetch_casual_cost_scoring(month: str, fiscal_year: str, supplier: str = "VF Farm Casual Wages", custom_department: str = "Processing"):
    """
    Compute Casual Cost (KES per Kg) scoring for a given Month and Fiscal Year.

    Returns dict with:
    - casual_costs_kes (Currency)
    - total_harvest_kg (Float)
    - casual_costs_per_kg (Float)
    - score (Int)
    - from_date, to_date (Date)
    """
    if not month or not fiscal_year:
        frappe.throw("Both Month and Fiscal Year are required")

    month_num = _month_name_to_number(month)
    if not month_num:
        frappe.throw(f"Invalid month: {month}")

    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    fy_start = getdate(fy.year_start_date)
    fy_end = getdate(fy.year_end_date)

    year = fy_start.year if month_num >= fy_start.month else fy_end.year
    from_date = getdate(f"{year}-{month_num:02d}-01")
    to_date = get_last_day(from_date)

    if not (fy_start <= from_date <= fy_end):
        frappe.throw(f"Selected month '{month}' does not fall within Fiscal Year '{fiscal_year}'.")

    casual_costs = _get_casual_costs(from_date, to_date, supplier, custom_department)
    harvest_qty = _get_harvest_qty(from_date, to_date)

    cost_per_kg = (casual_costs / harvest_qty) if harvest_qty else 0
    score_val = _score(cost_per_kg)

    return {
        "casual_costs_kes": round(casual_costs or 0, 2),
        "total_harvest_kg": round(harvest_qty or 0, 3),
        "casual_costs_per_kg": round(cost_per_kg or 0, 3),
        "score": int(score_val),
        "from_date": from_date,
        "to_date": to_date,
    }


@frappe.whitelist()
def fetch_casual_cost_scoring_for_cycle(appraisal_cycle: str, supplier: str = "VF Farm Casual Wages", custom_department: str = "Processing - VFL"):
    """Resolve month and fiscal year from Appraisal Cycle.start_date, then return scoring data."""
    if not appraisal_cycle:
        frappe.throw("Appraisal Cycle is required")

    cycle = frappe.get_doc("Appraisal Cycle", appraisal_cycle)
    if not getattr(cycle, "start_date", None):
        frappe.throw("Appraisal Cycle has no start_date")

    start = getdate(cycle.start_date)
    month_name = start.strftime("%B")
    fy_name = frappe.db.get_value(
        "Fiscal Year",
        {"year_start_date": ("<=", start), "year_end_date": (">=", start)},
        "name",
    )
    if not fy_name:
        frappe.throw("No Fiscal Year found for the Appraisal Cycle start date")

    return fetch_casual_cost_scoring(month_name, fy_name, supplier, custom_department)


def _month_name_to_number(name: str):
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


def _get_casual_costs(from_date, to_date, supplier: str, custom_department: str):
    return (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(grand_total), 0)
            FROM `tabPurchase Order`
            WHERE docstatus = 1
              AND supplier = %s
                            AND (IFNULL(custom_department, '') = %s OR custom_department = %s)
              AND transaction_date BETWEEN %s AND %s
            """,
                        (supplier, custom_department, custom_department, from_date, to_date),
        )[0][0]
        or 0
    )


def _get_harvest_qty(from_date, to_date):
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


def _score(value: float) -> int:
    if value <= 1.5:
        return 5
    if value <= 2:
        return 4
    if value <= 2.5:
        return 3
    if value < 4:
        return 2
    return 1
