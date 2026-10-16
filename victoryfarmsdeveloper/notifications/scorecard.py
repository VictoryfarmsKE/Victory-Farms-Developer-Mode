from email import message
import frappe
from datetime import datetime, timedelta

def send_pending_appraisal_notifications(batch_size=10):
    try:
        today = frappe.utils.getdate()
        if frappe.db.exists(
            "Email Queue",
            {
                "subject": ["like", "REMINDER: Scorecard Submission%"],
                "creation": [">", today],
            },
        ):
            return
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
                                    message = f"Hello {user_info['first_name']},<br><br>A reminder to complete and submit your scorecards by " + last_day_of_month.strftime("%B %d, %Y") + " at 5pm, as per the performance review timelines. <br><br><b>N/B Late Score Card Submission will reflect on the Manager's score card.</b> <br><br> "
                                    f"<b><a href=\"{url}\">{doc.name}</a></b> is pending your approval.<br><br> Reach out to HR in case of any challenges.<br><br>VF HR",
                                    now=True
                                )
                            except Exception as e:
                                frappe.log_error(f"Email error for {user_info['user']}: {e}", "Appraisals Notification Debug")
    except Exception as e:
        frappe.log_error(f"General error: {e}", "Appraisals Notification Debug")
      
#probation review notification
def send_probation_review_notifications():
    try:
        today = frappe.utils.getdate()
        target_date = today + timedelta(days=14)
        if frappe.db.exists(
            "Email Queue",
            {
                "subject": ["like", "Probation Review Reminder%"],
                "creation": [">", today],
            },
        ):
            return
        employees = frappe.get_all(
            "Employee",
            filters={"probation_end_date": target_date},
            fields=["name", "employee_name"],
        )

        if not employees:
            return
        hr_managers = frappe.db.sql(
            """
            SELECT u.name, u.first_name
            FROM `tabUser` u
            JOIN `tabHas Role` hr ON hr.parent = u.name
            WHERE hr.role = 'HR Manager'
              AND u.enabled = 1
              AND u.name NOT IN (
                  SELECT parent FROM `tabHas Role`
                  WHERE role = 'System Manager'
              )
            """,
            as_dict=True,
        )

        if not hr_managers:
            return
        rows = ""
        for emp in employees:
            url = frappe.utils.get_url_to_form("Employee", emp.name)
            rows += f"""
                <tr>
                    <td style="padding:6px 10px;border:1px solid #ddd;">
                        {emp.employee_name}
                    </td>
                    <td style="padding:6px 10px;border:1px solid #ddd;">
                        <a href="{url}">Open Record</a>
                    </td>
                </tr>
            """

        message_table = f"""
            <table style="border-collapse:collapse;font-family:Arial, sans-serif;font-size:13px;">
                <thead>
                    <tr style="background:#f2f2f2;">
                        <th style="padding:6px 10px;border:1px solid #ddd;">Employee</th>
                        <th style="padding:6px 10px;border:1px solid #ddd;">Link</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        """
        for hr in hr_managers:
            try:
                frappe.sendmail(
                    recipients=[hr["name"]],
                    subject=f"Probation Review Reminder - Reviews Due on {target_date.strftime('%B %d, %Y')}",
                    message=f"""
                        Hello {hr['first_name']},<br><br>

                        The following employees have probation reviews due on
                        <b>{target_date.strftime('%B %d, %Y')}</b>.<br><br>

                        Please initiate the probation review process.<br><br>

                        {message_table}

                        <br><br>
                        Thank you.<br>
                        <b>VF HR System</b>
                    """,
                    now=False,
                )

            except Exception as e:
                frappe.log_error(
                    f"Email error for {hr['name']}: {e}",
                    "Probation Review Notification Error",
                )

    except Exception as e:
        frappe.log_error(
            f"General error: {e}",
            "Probation Review Notification Failure",
        )


def queue_appraisal_notifications(doc, method):
    doc.load_doc_before_save()
    if not doc.has_value_changed("workflow_state"):
        return
    if getattr(doc, "workflow_state", None) not in ["Approved", "To Amend", "Cancelled"]:
        frappe.enqueue(
            "victoryfarmsdeveloper.notifications.scorecard.send_pending_appraisal_notifications",
            queue="short",
            timeout=600,
            is_async=True,
            job_name=f"Appraisal notification queue for {doc.name}"
        )


def send_pending_appraisal_notifications_summary():
    """
    Send summary notifications to managers for pending appraisals.
    Groups all pending appraisals by manager and sends one summary email per manager.
    Triggered on 19th, 23rd, 27th, and 30th of each month at 8:30 AM.
    """
    try:
        today = frappe.utils.getdate()
        day = today.day

        # Only run on 19th, 23rd, 27th, or 30th
        if day not in [19, 23, 27, 30]:
            return

        # Check if already sent today (prevent duplicates)
        if frappe.db.exists(
            "Email Queue",
            {
                "subject": ["like", "Action Required: % Pending Appraisal Approval(s)%"],
                "creation": [">", today],
            },
        ):
            return

        current_cycle = datetime.today().strftime("%B %Y")
        pending_appraisals = frappe.get_all(
            "Appraisal",
            filters={
                "workflow_state": ["not in", ["Approved", "To Amend", "Cancelled"]],
                "appraisal_cycle": current_cycle
            },
            fields=["name", "workflow_state", "employee"]
        )

        if not pending_appraisals:
            return

        # Group appraisals by manager
        manager_appraisals = {}
        for appraisal in pending_appraisals:
            doc = frappe.get_doc("Appraisal", appraisal.name)
            workflow = frappe.get_doc("Workflow", {"name": "Individual Appraisal"})

            for state in workflow.states:
                if state.state == doc.workflow_state:
                    role = state.allow_edit
                    manager = get_manager_for_role(doc.employee, role)
                    if manager:
                        if manager not in manager_appraisals:
                            manager_appraisals[manager] = []
                        manager_appraisals[manager].append(doc)
                    break

        # Send summary email per manager
        for manager_user, appraisals in manager_appraisals.items():
            send_summary_email(manager_user, appraisals)

    except Exception as e:
        frappe.log_error(f"General error: {e}", "Appraisal Summary Notification Debug")


def get_manager_for_role(employee, role):
    """
    Find the manager for a given employee and role by traversing the reports_to chain.
    Returns the user_id of the first eligible manager, or None if not found.
    """
    current_employee = employee
    for _ in range(5):
        reports_to = frappe.db.get_value("Employee", current_employee, "reports_to")
        if not reports_to:
            break
        user_id = frappe.db.get_value("Employee", reports_to, "user_id")
        has_role = frappe.db.exists("Has Role", {"role": role, "parent": user_id, "parenttype": "User"})
        is_enabled = frappe.db.get_value("User", user_id, "enabled") == 1
        is_sys_mgr = frappe.db.exists("Has Role", {"role": "System Manager", "parent": user_id, "parenttype": "User"})
        if has_role and is_enabled and not is_sys_mgr:
            return user_id
        current_employee = reports_to
    return None


def send_summary_email(manager_user, appraisals):
    """
    Send a summary email to a manager with all their pending appraisals.
    """
    try:
        manager_name = frappe.db.get_value("User", manager_user, "first_name")

        # Build HTML table
        rows = ""
        for appraisal in appraisals:
            employee_name = frappe.db.get_value("Employee", appraisal.employee, "employee_name")
            department = frappe.db.get_value("Employee", appraisal.employee, "department")
            url = frappe.utils.get_url_to_form("Appraisal", appraisal.name)

            rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{employee_name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{department}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{appraisal.workflow_state}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <a href="{url}">Review Appraisal</a>
                    </td>
                </tr>
            """

        message_table = f"""
            <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Employee</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Department</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Status</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        """

        frappe.sendmail(
            recipients=[manager_user],
            subject=f"Action Required: {len(appraisals)} Pending Appraisal Approval(s) - {manager_name}",
            message=f"""
                Hello {manager_name},<br><br>
                You have {len(appraisals)} appraisal approval(s) pending your review.<br><br>
                {message_table}
                <br><br>
                Please complete these appraisals by the end of the month.<br><br>
                VF HR
            """,
            now=True
        )

    except Exception as e:
        frappe.log_error(f"Email error for {manager_user}: {e}", "Appraisal Summary Notification Debug")

