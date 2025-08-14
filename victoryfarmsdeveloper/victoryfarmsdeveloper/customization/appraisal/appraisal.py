import frappe
from frappe.utils import has_common
from datetime import datetime, timedelta

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
                        current_employee = doc.employee
                        notified_users = []
                        # Traverse up the reports_to chain, but stop at the first eligible user
                        for _ in range(5):
                            reports_to = frappe.db.get_value("Employee", current_employee, "reports_to")
                            if not reports_to:
                                break
                            user_id = frappe.db.get_value("Employee", reports_to, "user_id")
                            has_role = frappe.db.exists("Has Role", {"role": role, "parent": user_id, "parenttype": "User"})
                            is_enabled = frappe.db.get_value("User", user_id, "enabled") == 1
                            is_sys_mgr = frappe.db.exists("Has Role", {"role": "System Manager", "parent": user_id, "parenttype": "User"})
                            if has_role and is_enabled and not is_sys_mgr:
                                first_name = frappe.db.get_value("User", user_id, "first_name")
                                notified_users.append({"user": user_id, "first_name": first_name})
                                break  # Stop after finding the first eligible user
                            current_employee = reports_to

                        for user_info in notified_users:
                            try:
                                url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
                                last_day_of_month = (datetime.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                                frappe.sendmail(
                                    recipients=[user_info["user"]],
                                    subject="REMINDER: Scorecard Submission Due by " + last_day_of_month.strftime("%B %d, %Y"),
                                    message = f"Hello {user_info['first_name']},<br><br>A reminder to complete and submit your scorecards by " + last_day_of_month.strftime("%B %d, %Y") + " at 5pm, as per the performance review timelines. <b>N/B Late Score Card Submission will reflect on the Manager’s score card.</b> <br><br><a href=\"{url}\">{doc.name}</a> is pending your approval.<br><br> Reach out to Angeline/Anne in case of any challenges.<br><br>VF HR.",
                                    now=True
                                )
                            except Exception as e:
                                frappe.log_error(f"Email error for {user_info['user']}: {e}", "Appraisals Notification Debug")
    except Exception as e:
        frappe.log_error(f"General error: {e}", "Appraisals Notification Debug")
      