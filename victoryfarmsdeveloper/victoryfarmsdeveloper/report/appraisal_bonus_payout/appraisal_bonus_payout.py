# Copyright (c) 2024, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

AppraisalPayout = frappe.qb.DocType("Appraisal Payout")
AppraisalPayoutItem = frappe.qb.DocType("Appraisal Payout Item")

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

    return columns, data

def get_appraisal_payout_details(filtered_appraisal_payouts):
    payout_ids = [payout['name'] for payout in filtered_appraisal_payouts]
    
    if not payout_ids:
        return []

    # Query the payout items for the filtered payout IDs
    return (
        frappe.qb.from_(AppraisalPayoutItem)
        .join(AppraisalPayout).on(AppraisalPayout.name == AppraisalPayoutItem.parent)
        .where(AppraisalPayoutItem.parent.isin(payout_ids)) 
        .where(AppraisalPayoutItem.total_bonus != 0)
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

    query = frappe.qb.from_(AppraisalPayout ).select(
        AppraisalPayout.name,
        AppraisalPayout.company,
        AppraisalPayout.payout_frequency,
        AppraisalPayout.start_date,
        AppraisalPayout.end_date,
        AppraisalPayout.posting_date
    )
    
    if conditions:
        for condition in conditions:
            query = query.where(condition)

    return query.run(as_dict=True)

def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        # {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 140},
        # {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 160},
        {"label": _("Payout Frequency"), "fieldname": "payout_frequency", "fieldtype": "Select", "width": 120},
        # {"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 120},
        # {"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 120},
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
        {"label": _("Individual Score"), "fieldname": "individual_score", "fieldtype": "Percent", "width": 120},
        {"label": _("Individual Bonus"), "fieldname": "individual_bonus", "fieldtype": "Currency", "width": 120},
        {"label": _("Department Score"), "fieldname": "department_score", "fieldtype": "Percent", "width": 120},
        {"label": _("Department Bonus"), "fieldname": "department_bonus", "fieldtype": "Currency", "width": 120},
        {"label": _("Company Score"), "fieldname": "company_score", "fieldtype": "Percent", "width": 120},
        {"label": _("Company Bonus"), "fieldname": "company_bonus", "fieldtype": "Currency", "width": 120},
        {"label": _("Total Bonus"), "fieldname": "total_bonus", "fieldtype": "Currency", "width": 120},
    ]
