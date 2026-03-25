import frappe
from frappe.utils import has_common

def get_subordinates(employee):
    """Recursively get all employees whose reporting line leads back to the given employee."""
    subordinates = []
    direct_reports = frappe.get_all(
        "Employee",
        filters={"reports_to": employee, "status": "Active"},
        pluck="name"
    )
    for report in direct_reports:
        subordinates.append(report)
        subordinates.extend(get_subordinates(report))
    return subordinates

def has_permission(doc, ptype, user):
    if ptype != "read":
        return None
    
    admin_roles = ["HR Manager", "Payroll Officer"]
    user_roles = frappe.get_roles(user)
    if has_common(user_roles, admin_roles):
        return True

    employee = frappe.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return False

    if doc.employee == employee and doc.docstatus == 1 and doc.workflow_state == "Approved":
        return True

    if "HR User" in user_roles:
        subordinates = get_subordinates(employee)
        if doc.employee in subordinates:
            return True

    return False

def get_permission_query_conditions(user):
    if not user:
        return ""

    admin_roles = ["HR Manager", "Payroll Officer"]
    user_roles = frappe.get_roles(user)
    employee = frappe.get_value("Employee", {"user_id": user}, "name")

    if has_common(user_roles, admin_roles):
        if employee:
            escaped = frappe.db.escape(employee)
            return f"""((`tabAppraisal`.employee != {escaped}) OR 
                        (`tabAppraisal`.employee = {escaped} AND 
                         `tabAppraisal`.docstatus = 1))"""
        return ""

    if not employee:
        return "1=0"

    escaped = frappe.db.escape(employee)

    if "HR User" in user_roles:
        subordinates = get_subordinates(employee)
        if subordinates:
            escaped_subs = ", ".join(frappe.db.escape(s) for s in subordinates)
            return f"""(`tabAppraisal`.employee IN ({escaped_subs}) OR 
                        (`tabAppraisal`.employee = {escaped} AND 
                         `tabAppraisal`.docstatus = 1 AND 
                         `tabAppraisal`.workflow_state = 'Approved'))"""

    return f"""(`tabAppraisal`.employee = {escaped} 
              AND `tabAppraisal`.docstatus = 1 
              AND `tabAppraisal`.workflow_state = 'Approved')"""