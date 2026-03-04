import frappe

def has_permission(doc, ptype, user):
    #Managers may view submitted LDCs of their direct reports (docstatus == 1)
    if "System Manager" in frappe.get_roles(user):
        return True

    employee = frappe.get_value("Employee", {"user_id": user}, "name")

    if employee and doc.employee == employee:
        return True
    if ptype == "read" and employee:
        if doc.docstatus == 1 and doc.reports_to:
            if doc.reports_to == employee:
                return True
    return False


def get_permission_query_conditions(user):
    #permission filter for list views.
    if not user:
        return ""
    full_access_roles = ["System Manager", "HR Manager"]
    if any(r in frappe.get_roles(user) for r in full_access_roles):
        return ""

    employee = frappe.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return "1=0"

    return f"((`tabLeadership Development Card`.employee = '{employee}') OR (`tabLeadership Development Card`.reports_to = '{employee}' AND `tabLeadership Development Card`.docstatus = 1))"
