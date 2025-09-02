import frappe
from frappe.utils import has_common

def has_permission(doc, ptype, user):
    if ptype != "read":
        return None

    # Allow full access to specific roles
    full_access_roles = [
        "HR Manager",
        "HR User",
        "Payroll Officer"
    ]

    user_roles = frappe.get_roles(user)
    if has_common(user_roles, full_access_roles):
        return True

    # Allow employees to see their own completed appraisals
    employee = frappe.get_value("Employee", {"user_id": user}, "name")
    if employee and doc.employee == employee and doc.docstatus == 1 and doc.workflow_state == "Approved":
        return True

    return False

def get_permission_query_conditions(user):
    if not user:
        return ""

    full_access_roles = [
        "HR Manager",
        "HR User",
        "Payroll Officer"
    ]

    user_roles = frappe.get_roles(user)
    employee = frappe.get_value("Employee", {"user_id": user}, "name")

    # If the user has full access roles
    if has_common(user_roles, full_access_roles):
        if employee:
            # Exclude the user's own draft appraisal records but include approved ones
            return f"""((`tabAppraisal`.employee != '{employee}') OR 
                        (`tabAppraisal`.employee = '{employee}' AND 
                         `tabAppraisal`.docstatus = 1))"""
        return ""

    # If the user is an "normal" employee, show only their completed appraisals
    if employee:
        return f"""(`tabAppraisal`.employee = '{employee}' 
                  and `tabAppraisal`.docstatus = 1 
                  and `tabAppraisal`.workflow_state = 'Approved')"""

    # If no employee record is found, show nothing
    return "1=0"