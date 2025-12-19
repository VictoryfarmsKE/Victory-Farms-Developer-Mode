import frappe
from frappe.utils import has_common


def get_all_reports(employee, visited=None):
    """Recursively get all employees reporting to this employee (full hierarchy)."""
    if visited is None:
        visited = set()
    if employee in visited:
        return []
    visited.add(employee)

    direct_reports = frappe.get_all("Employee", filters={"reports_to": employee}, pluck="name") or []
    all_reports = list(direct_reports)
    for report in direct_reports:
        all_reports.extend(get_all_reports(report, visited))
    return all_reports


def has_permission(doc, ptype, user):
    if ptype != "read":
        return None

    # Allow full access to specific roles
    full_access_roles = ["HR Manager", "Payroll Officer"]

    if has_common(frappe.get_roles(user), full_access_roles):
        return True

    # Resolve employee for the user
    employee = frappe.get_value("Employee", {"user_id": user}, "name")

    EXCLUDED_CYCLES = ["October 2025", "November 2025", "December 2025"]
    EXCLUDED_TEMPLATES = [
        "M/D/C Appraisal Scorecard Template",
        "M/D/C Appraisal Scorecard Template(new joiners)"
    ]

    appraisal_cycle = getattr(doc, "appraisal_cycle", "") or ""
    appraisal_template = getattr(doc, "appraisal_template", "") or ""

    # All downstream reports (full hierarchy)
    all_reports = []
    if employee:
        all_reports = get_all_reports(employee)

    # Managers can see draft or approved appraisals of all downstream reports
    if employee and doc.employee in all_reports and doc.docstatus in (0, 1):
        return True

    # Helper: case-insensitive contains check
    def _contains_any(val, lst):
        v = (val or "").lower()
        return any(x.lower() in v for x in lst)

    # Deny the employee themself only when BOTH cycle and template match the excluded lists
    if (
        employee
        and doc.employee == employee
        and _contains_any(appraisal_cycle, EXCLUDED_CYCLES)
        and _contains_any(appraisal_template, EXCLUDED_TEMPLATES)
    ):
        return False

    # Allow employee to see their own approved appraisals (non-excluded)
    if employee and doc.employee == employee and doc.docstatus == 1 and doc.workflow_state == "Approved":
        return True

    return False


def get_permission_query_conditions(user):
    if not user:
        return ""

    full_access_roles = ["HR Manager", "Payroll Officer"]

    if has_common(frappe.get_roles(user), full_access_roles):
        employee = frappe.get_value("Employee", {"user_id": user}, "name")
        if employee:
            # Exclude the user's own draft appraisal records but include approved ones
            return f"""((`tabAppraisal`.employee != '{employee}') OR 
                        (`tabAppraisal`.employee = '{employee}' AND 
                         `tabAppraisal`.docstatus = 1))"""
        return ""

    # Normal employee
    employee = frappe.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return "1=0"

    EXCLUDED_CYCLES = ["October 2025", "November 2025", "December 2025"]
    EXCLUDED_TEMPLATES = [
        "M/D/C Appraisal Scorecard Template",
        "M/D/C Appraisal Scorecard Template(new joiners)"
    ]

    # Build LIKE conditions for cycles to be robust against formatting differences
    cycles_like = " OR ".join([f"`tabAppraisal`.appraisal_cycle LIKE '%{c}%'" for c in EXCLUDED_CYCLES])
    templates_list = "','".join(EXCLUDED_TEMPLATES)

    self_clause = (
        f"(`tabAppraisal`.employee = '{employee}' AND `tabAppraisal`.docstatus = 1 AND `tabAppraisal`.workflow_state = 'Approved' "
        f"AND NOT (({cycles_like}) AND `tabAppraisal`.appraisal_template IN ('{templates_list}')))"
    )

    # Include all downstream reports (full hierarchy) with drafts and approved (docstatus 0 or 1)
    all_reports = get_all_reports(employee)
    if all_reports:
        reports_list = "','".join(all_reports)
        reports_clause = f"(`tabAppraisal`.employee IN ('{reports_list}') AND `tabAppraisal`.docstatus IN (0,1))"
        return f"({self_clause} OR {reports_clause})"

    return self_clause