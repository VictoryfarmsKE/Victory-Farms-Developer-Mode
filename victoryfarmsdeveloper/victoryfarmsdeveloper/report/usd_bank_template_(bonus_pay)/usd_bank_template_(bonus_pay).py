# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt

AppraisalPayout = frappe.qb.DocType("Appraisal Payout")
AppraisalPayoutItem = frappe.qb.DocType("Appraisal Payout Item")
Employee = frappe.qb.DocType("Employee")

def execute(filters=None):

    filters = filters or {}

    filtered_appraisal_payouts = get_appraisal_payouts(filters)
    if not filtered_appraisal_payouts:
        return [], []

    columns = get_columns()
    
    appraisal_payout_items = get_appraisal_payout_details(filtered_appraisal_payouts)

    data = [
        {
            "company": item["company"],
            "payout_frequency": item["payout_frequency"],
            "start_date": item["start_date"],
            "end_date": item["end_date"],
            "posting_date": item["posting_date"],
            "employee": item["employee"],
            "employee_name": item["employee_name"],
            "department": item["department"],
            "individual_score": item["individual_score"],
            "individual_bonus": item["individual_bonus"],
            "department_score": item["department_score"],
            "department_bonus": item["department_bonus"],
            "company_score": item["company_score"],
            "company_bonus": item["company_bonus"],
            "total_bonus": item["total_bonus"]
        }
        for item in appraisal_payout_items
    ]

    # Enrich rows with bank template fields from Employee and map total_bonus to payment fields
    if data:
        emp_ids = list({row["employee"] for row in data if row.get("employee")})
        emp_bank_map = get_employee_bank_map(emp_ids)

        for row in data:
            emp = row.get("employee")
            emp_info = emp_bank_map.get(emp, {})
            row["beneficiary_name"] = row.get("employee_name") or emp_info.get("employee_name")
            row["transaction_currency"] = emp_info.get("salary_currency") or None
            row["payment_amount"] = flt(row.get("total_bonus") or 0)

    return columns, data

def get_appraisal_payout_details(filtered_appraisal_payouts):
    payout_ids = [payout['name'] for payout in filtered_appraisal_payouts]
    
    if not payout_ids:
        return []

    # Query the payout items for the filtered payout IDs
    return (
        frappe.qb.from_(AppraisalPayoutItem)
        .join(AppraisalPayout).on(AppraisalPayout.name == AppraisalPayoutItem.parent)
        .join(Employee).on(Employee.name == AppraisalPayoutItem.employee)
        .where(AppraisalPayoutItem.parent.isin(payout_ids))
        .where(AppraisalPayoutItem.total_bonus != 0)
        .where(Employee.salary_currency == "USD")
        .select(
            AppraisalPayoutItem.employee,
            AppraisalPayoutItem.employee_name,
            AppraisalPayoutItem.department,
            AppraisalPayoutItem.individual_score,
            AppraisalPayoutItem.individual_bonus,
            AppraisalPayoutItem.department_score,
            AppraisalPayoutItem.department_bonus,
            AppraisalPayoutItem.company_score,
            AppraisalPayoutItem.company_bonus,
            AppraisalPayoutItem.total_bonus,
            AppraisalPayout.company,
            AppraisalPayout.payout_frequency,
            AppraisalPayout.start_date,
            AppraisalPayout.end_date,
            AppraisalPayout.posting_date
        )
        .distinct()
        .run(as_dict=True)
    )

def get_appraisal_payouts(filters):
    conditions = []

    if filters.get("start_date"):
        conditions.append(AppraisalPayout.start_date >= filters["start_date"])
    if filters.get("end_date"):
        conditions.append(AppraisalPayout.end_date <= filters["end_date"])
    if filters.get("company"):
        conditions.append(AppraisalPayout.company == filters["company"])
    if filters.get("payout_frequency"):
        conditions.append(AppraisalPayout.payout_frequency == filters["payout_frequency"])
    if filters.get("posting_date"):
        conditions.append(AppraisalPayout.posting_date == filters["posting_date"])

    query = frappe.qb.from_(AppraisalPayout).select(
        AppraisalPayout.name,
        AppraisalPayout.company,
        AppraisalPayout.payout_frequency,
        AppraisalPayout.start_date,
        AppraisalPayout.end_date,
        AppraisalPayout.posting_date
    ).where(AppraisalPayout.docstatus == 1)
    
    if conditions:
        for condition in conditions:
            query = query.where(condition)

    return query.run(as_dict=True)

def get_columns():
    cols = [
        {"fieldname": "beneficiary_name", "label": _("Beneficiary Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "transaction_currency", "label": _("Transaction Currency"), "fieldtype": "Link", "options": "Currency", "width": 100},
        {"fieldname": "payment_amount", "label": _("Net Pay"), "fieldtype": "Float", "width": 120},
    ]

    return cols


def get_employee_bank_map(employee_ids):
    if not employee_ids:
        return {}
    rows = frappe.db.sql(
        """
        SELECT name, employee_name, bank_ac_no, custom_bank_code, custom_branch_code, salary_currency, bank_name
        FROM `tabEmployee`
        WHERE name IN %(emp_ids)s
        """,
        {"emp_ids": tuple(employee_ids)},
        as_dict=True,
    )
    return {r["name"]: r for r in rows}
