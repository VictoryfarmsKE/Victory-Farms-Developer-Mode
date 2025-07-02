import hrms
import frappe
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

def leave_balance_update_check():
    """
    This function checks for pending leave applications and sends notifications
    to employees when their leave balance is sufficient for the requested leave.
    """
    try:
        pending_apps = frappe.get_all(
            "Leave Application",
            filters={"status": "Pending Sufficient Balance", "docstatus": 0},
            fields=["name", "employee", "leave_type", "from_date", "to_date", "total_leave_days"]
        )

        for app in pending_apps:
            try:
                leave_balance = get_leave_balance_on(
                    app["employee"],
                    app["leave_type"],
                    app["from_date"],
                    app["to_date"],
                    consider_all_leaves_in_the_allocation_period=True,
                    for_consumption=True,
                )
                leave_balance_for_consumption = leave_balance.get("hrms.hr.doctype.leave_application.leave_application.leave_balance_for_consumption", 0)
                if leave_balance_for_consumption >= app["total_leave_days"]:
                    employee_user = frappe.db.get_value("Employee", app["employee"], "user_id")
                    doc = frappe.get_doc("Leave Application", app.name)
                    url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
                    if employee_user:
                        subject = "Your Leave Balance is Now Sufficient"
                        message = (
                            f"Dear Employee,<br><br>"
                            f"Your leave balance for <b>{app['leave_type']}</b> is now sufficient to approve your leave application "
                            f"<b><a href=\"{url}\">{doc.name}</a></b> from <b>{app['from_date']}</b> to <b>{app['to_date']}</b>.<br>"
                            f"Please contact your approver or re-open if required.<br><br>"
                        )
                        try:
                            frappe.sendmail(
                                recipients=[employee_user],
                                subject=subject,
                                message=message,
                            )
                        except Exception as mail_err:
                            # return mail_err
                            frappe.log_error(f"Email error for {employee_user}: {mail_err}", "Leave Balance Notification")
            except Exception as app_err:
                frappe.log_error(f"Error processing Leave Balance Notification {app['name']}: {app_err}", "Leave Balance Notification")
    except Exception as e:
        return e
    
def create_employee_folders():
    batch_size = 5
    folders = ["Employment", "Disciplinary", "Performance Management", "Payroll Administration"]
    employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
    # log(employees)
    for i in range(0, len(employees), batch_size):
        batch = employees[i:i+batch_size]

        for emp in batch:
            try:
                parent_folder = f"Home/Employee Documents/{emp}"
        
                # Ensure Employee folder exists
                if not frappe.db.exists("File", {"file_name": emp, "folder": "Home/Employee Documents", "is_folder": 1}):
                    frappe.get_doc({
                        "doctype": "File",
                        "file_name": emp,
                        "folder": "Home/Employee Documents",
                        "is_folder": 1,
                        "is_private": 1
                    }).insert(ignore_permissions=True)
        
                # Create subfolders under Employee folder
                for subfolder in folders:
                    if not frappe.db.exists("File", {"file_name": subfolder, "folder": parent_folder, "is_folder": 1}):
                        frappe.get_doc({
                            "doctype": "File",
                            "file_name": subfolder,
                            "folder": parent_folder,
                            "is_folder": 1,
                            "is_private": 1
                        }).insert(ignore_permissions=True)
        
            except Exception as e:
                frappe.log_error(title="Folder Creation Error", message=f"Employee: {emp} — {e}")
        
        frappe.db.commit()