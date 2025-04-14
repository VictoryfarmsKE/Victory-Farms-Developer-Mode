import frappe
from frappe.utils import has_common

def has_permission(doc, ptype, user):
    if ptype != "read":
        return None

    # Allow full access to specific roles
    full_access_roles = [
        "Department Appraisal Bulk Updater",
        "System Manager",
        "Executive Manager",
        "Payroll Officer"
    ]

    user_roles = frappe.get_roles(user)
    if has_common(user_roles, full_access_roles):
        return True

    # For employees, restrict to their own department
    employee = frappe.get_value("Employee", {"user_id": user}, ["department"])
    if employee and doc.department == employee:
        return True

    return False

def get_permission_query_conditions(user):
    if not user:
        return ""

    full_access_roles = [
        "Department Appraisal Bulk Updater",
        "System Manager",
        "Executive Manager",
        "Payroll Officer"
    ]

    user_roles = frappe.get_roles(user)
    if has_common(user_roles, full_access_roles):
        return ""

    employee_department = frappe.db.get_value("Employee", {"user_id": user}, "department")
    if employee_department:
        return f"""(`tabDepartment Appraisal`.department = '{employee_department}')"""

    # If no department is found, show nothing
    return "1=0"