import frappe
from frappe.utils import has_common
from datetime import datetime

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


def send_pending_appraisal_notifications(batch_size=10):
    try:
        current_cycle = datetime.today().strftime("%B %Y")
        pending_appraisals = frappe.get_all(
            "Appraisal",
            filters={"workflow_state": ["not in", ["Approved", "To Amend"]],
                    "appraisal_cycle": current_cycle
            },
            fields=["name", "workflow_state"]
        )
        frappe.log_error(f"Pending appraisals count: {len(pending_appraisals)}", "Appraisals Notification Debug")
        total = len(pending_appraisals)
        for batch_start in range(0, total, batch_size):
            batch = pending_appraisals[batch_start:batch_start+batch_size]
            for appraisal in batch:
                doc = frappe.get_doc("Appraisal", appraisal.name)
                # Get the workflow for Appraisal
                workflow = frappe.get_doc("Workflow", {"name": "Individual Appraisal"})
                for state in workflow.states:
                    if state.state == doc.workflow_state:
                        role = state.allow_edit
                        # Get users with the role, but exclude those who are System Managers
                        users = frappe.get_all(
                            "Has Role",
                            filters={"role": role, "parenttype": "User"},
                            fields=["parent"]
                        )
                        filtered_users = []
                        for u in users:
                            # Exclude users who have the "System Manager" role
                            has_sys_mgr = frappe.db.exists(
                                "Has Role",
                                {"role": "System Manager", "parent": u.parent, "parenttype": "User"}
                            )
                            if not has_sys_mgr and frappe.db.get_value("User", u.parent, "enabled") == 1:
                                first_name = frappe.db.get_value("User", u.parent, "first_name")
                                filtered_users.append({"user": u.parent, "first_name": first_name})
                        for user_info in filtered_users:
                            try:
                                url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
                                # frappe.sendmail(
                                #     recipients=[user_info["user"]],
                                #     subject="Daily summary: Appraisal(s) Pending Approval",
                                #     message = f"Hello {user_info['first_name']},<br><br>Appraisal <b><a href=\"{url}\">{doc.name}</a></b> is pending your approval.<br>",
                                #     now=True
                                # )
                            except Exception as e:
                                frappe.log_error(f"Email error for {user_info['user']}: {e}", "Appraisals Notification Debug")
    except Exception as e:
        frappe.log_error(f"General error: {e}", "Appraisals Notification Debug")
      