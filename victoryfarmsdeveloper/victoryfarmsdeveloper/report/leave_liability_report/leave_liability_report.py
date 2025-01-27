# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

LeaveAllocation = frappe.qb.DocType("Leave Allocation")
Employee = frappe.qb.DocType("Employee")

def execute(filters=None):
    filters = filters or {}

    filtered_leave_allocations = get_leave_allocations(filters)
    if not filtered_leave_allocations:
        return [], []

    columns = get_columns()
    
    leave_allocation_items = get_leave_allocations_details(filtered_leave_allocations)

    data = [
        {
            "leave_type": item["leave_type"],
            "from_date": item["from_date"],
            "to_date": item["to_date"],
            "employee": item["employee"],
            "employee_name": item["employee_name"],
            "department": item["department"],
            "total_leaves_allocated": item["total_leaves_allocated"],
            "ctc": item["ctc"]/31,
            "employee_number": item["employee_number"],
            "leave_liability": item["total_leaves_allocated"] * item["ctc"]/31
        }
        for item in leave_allocation_items
    ]

    return columns, data

def get_leave_allocations_details(filtered_leave_allocations):
    leave_allocation_ids = [leave_allocation['name'] for leave_allocation in filtered_leave_allocations]
    
    if not leave_allocation_ids:
        return []

    return (
        frappe.qb.from_(LeaveAllocation)
        .join(Employee).on(LeaveAllocation.employee == Employee.name)
        .where(LeaveAllocation.name.isin(leave_allocation_ids)) 
        .select(
            LeaveAllocation.employee,
            Employee.employee_name,
            Employee.ctc,
            Employee.employee_number,
            Employee.department,
            LeaveAllocation.leave_type,
            LeaveAllocation.from_date,
            LeaveAllocation.to_date,
            LeaveAllocation.total_leaves_allocated
        )
        .run(as_dict=True)
    )

def get_leave_allocations(filters):
    conditions = []

    if filters.get("from_date"):
        conditions.append(LeaveAllocation.from_date >= filters["from_date"])
    if filters.get("to_date"):
        conditions.append(LeaveAllocation.to_date <= filters["to_date"])
    if filters.get("department"):
        conditions.append(LeaveAllocation.department == filters["department"])
    if filters.get("leave_type"):
        conditions.append(LeaveAllocation.leave_type == filters["leave_type"])

    query = frappe.qb.from_(LeaveAllocation ).select(
        LeaveAllocation.name,
        LeaveAllocation.department,
        LeaveAllocation.leave_type,
        LeaveAllocation.from_date,
        LeaveAllocation.to_date
    )
    
    if conditions:
        for condition in conditions:
            query = query.where(condition)

    return query.run(as_dict=True)

def get_columns():
    return [
        {"label": _("Employee Number"), "fieldname": "employee_number", "fieldtype": "Data", "width": 140},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 200},
        {"label": _("To Date"), "fieldname": "to_date", "fieldtype": "Date", "width": 120},
        {"label": _("From Date"), "fieldname": "from_date", "fieldtype": "Date", "width": 120},
        {"label": _("Leave Type"), "fieldname": "leave_type", "fieldtype": "Data", "width": 120},
        {"label": _("Total Leaves Allocated"), "fieldname": "total_leaves_allocated", "fieldtype": "Float", "width": 180},
        {"label": _("Daily CTC"), "fieldname": "ctc", "fieldtype": "Currency", "width": 160},
        {"label": _("Leave Liability"), "fieldname": "leave_liability", "fieldtype": "Currency", "width": 160},
    ]