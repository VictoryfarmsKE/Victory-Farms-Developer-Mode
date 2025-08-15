import datetime
import frappe
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
from frappe.utils import today, get_first_day, get_last_day, add_months

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

def create_long_weekend_leave_allocation():
    leave_type = "Long Weekend"
    today_date = today()

    try:
        start_of_month = get_first_day(today_date)
        end_of_month = get_last_day(today_date)

        employees = frappe.get_all(
            "Employee",
            filters={
                "status": "Active",
                "custom_location": "Roo Bay Farm",
                "grade": ("like", "M%")
            },
            fields=["name"]
        )

        created_count = 0

        for emp in employees:
            exists = frappe.db.exists(
                "Leave Allocation",
                {
                    "employee": emp.name,
                    "leave_type": leave_type,
                    "from_date": start_of_month,
                    "to_date": end_of_month,
                    "docstatus": ["!=", 2]
                }
            )
            if not exists:
                try:
                    doc = frappe.new_doc("Leave Allocation")
                    doc.employee = emp.name
                    doc.leave_type = leave_type
                    doc.from_date = start_of_month
                    doc.to_date = end_of_month
                    doc.new_leaves_allocated = 2.0
                    doc.total_leaves_allocated = 2.0
                    doc.carry_forward = False
                    doc.ignore_validate = True
                    doc.save()
                    doc.submit()
                    frappe.db.commit()
                    created_count += 1
                except Exception as e:
                    frappe.log_error(
                        title="Leave Allocation Error",
                        message=f"Failed for Employee: {emp.name}\nError: {frappe.get_traceback()}"
                    )

        frappe.log_error(
            title="Long Weekend Leave Allocation Summary",
            message=f"{created_count} leave allocations created on {today_date}."
        )

    except Exception as e:
        frappe.log_error(
            title="Leave Allocation Script Failure",
            message=frappe.get_traceback()
        )


def create_employee_folders(employee_names):
    folders = ["Employment", "Disciplinary", "Performance Management", "Payroll Administration"]
    current_year = int(frappe.utils.nowdate()[:4])

    for emp_name in employee_names:
        try:
            emp = frappe.get_doc("Employee", emp_name)
            if not emp.date_of_joining:
                continue

            parent_folder = f"Home/Employee Documents/{emp.name}"

            # Step 1: Create the main Employee folder
            if not frappe.db.exists("File", {"file_name": emp.name, "folder": "Home/Employee Documents", "is_folder": 1}):
                frappe.get_doc({
                    "doctype": "File",
                    "file_name": emp.name,
                    "folder": "Home/Employee Documents",
                    "is_folder": 1,
                    "is_private": 1
                }).insert(ignore_permissions=True)

            # Step 2: Determine year range
            start_year = emp.date_of_joining.year
            end_year = emp.relieving_date.year if emp.relieving_date else current_year
            years = range(start_year, end_year + 1)

            # Step 3: Create subfolders and year folders
            for subfolder in folders:
                subfolder_path = f"{parent_folder}/{subfolder}"
                
                # Create subfolder
                if not frappe.db.exists("File", {"file_name": subfolder, "folder": parent_folder, "is_folder": 1}):
                    frappe.get_doc({
                        "doctype": "File",
                        "file_name": subfolder,
                        "folder": parent_folder,
                        "is_folder": 1,
                        "is_private": 1
                    }).insert(ignore_permissions=True)

                # Create year folders
                for year in years:
                    year_folder = str(year)
                    if not frappe.db.exists("File", {"file_name": year_folder, "folder": subfolder_path, "is_folder": 1}):
                        frappe.get_doc({
                            "doctype": "File",
                            "file_name": year_folder,
                            "folder": subfolder_path,
                            "is_folder": 1,
                            "is_private": 1
                        }).insert(ignore_permissions=True)

        except Exception as e:
            frappe.log_error(title="Employee Folder Creation Error", message=f"{emp_name}: {e}")

    frappe.db.commit()

def enqueue_employee_folder_creation(batch_size=5):
    employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
    for i in range(0, len(employees), batch_size):
        batch = employees[i:i+batch_size]
        frappe.enqueue(
            method="victoryfarmsdeveloper.notifications.leave_balance_update_check.create_employee_folders",
            queue="long",
            timeout=None,
            is_async=True,
            employee_names=batch,
            job_name=f"Create folders for employees [{batch[0]} - {batch[-1]}]"
        )
        
def process_checkins_without_shift(batch_size=250, start=0):
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"shift": ["is", "not set"]},
        fields=["name"],
        start=start,
        page_length=batch_size
    )
    checkin_names = [c.name for c in checkins]
    if checkin_names:
        # Your logic to update/fetch shift for these checkins
        frappe.call("hrms.hr.doctype.employee_checkin.employee_checkin.bulk_fetch_shift", checkins=checkin_names)
        # If batch was full, there may be more to process
        if len(checkin_names) == batch_size:
            frappe.enqueue(
                "victoryfarmsdeveloper.notifications.leave_balance_update_check.process_checkins_without_shift",
                batch_size=batch_size,
                start=start + batch_size,
                queue="long",
                timeout=600,
                is_async=True
            )
            
@frappe.whitelist()
def start_background_shift_update():
    frappe.enqueue(
        "victoryfarmsdeveloper.notifications.leave_balance_update_check.process_checkins_without_shift",
        batch_size=100,
        start=0,
        queue="long",
        timeout=600,
        is_async=True
    )