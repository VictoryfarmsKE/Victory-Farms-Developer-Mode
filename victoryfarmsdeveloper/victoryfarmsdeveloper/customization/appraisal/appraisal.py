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

    # Allow employees to see their own completed appraisals, except for certain cycles/templates
    employee = frappe.get_value("Employee", {"user_id": user}, "name")

    EXCLUDED_CYCLES = ["October 2025", "November 2025", "December 2025"]
    EXCLUDED_TEMPLATES = [
        "M/D/C Appraisal Scorecard Template",
        "M/D/C Appraisal Scorecard Template(new joiners)"
    ]

    appraisal_cycle = getattr(doc, "appraisal_cycle", None)
    appraisal_template = getattr(doc, "appraisal_template", None)

    # If this is one of the excluded cycles/templates, employees (non-full-access) cannot view it
    if employee and doc.employee == employee and appraisal_cycle in EXCLUDED_CYCLES and appraisal_template in EXCLUDED_TEMPLATES:
        return False

    if employee and doc.employee == employee and doc.docstatus == 0 and doc.workflow_state == "Approved":
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
        EXCLUDED_CYCLES = ["October 2025", "November 2025", "December 2025"]
        EXCLUDED_TEMPLATES = [
            "M/D/C Appraisal Scorecard Template",
            "M/D/C Appraisal Scorecard Template(new joiners)"
        ]

        cycles_list = "','".join(EXCLUDED_CYCLES)
        templates_list = "','".join(EXCLUDED_TEMPLATES)

        return f"""(`tabAppraisal`.employee = '{employee}' 
                  and `tabAppraisal`.docstatus = 1 
                  and `tabAppraisal`.workflow_state = 'Approved' 
                  and NOT (`tabAppraisal`.appraisal_cycle IN ('{cycles_list}') 
                           AND `tabAppraisal`.appraisal_template IN ('{templates_list}')))"""

    # If no employee record is found, show nothing
    return "1=0"