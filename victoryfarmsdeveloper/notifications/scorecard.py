import frappe
from datetime import datetime, timedelta

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

        current_cycle = datetime.today().strftime("%B %Y")
        pending_appraisals = frappe.get_all(
            "Appraisal",
            filters={
                "workflow_state": ["not in", ["Approved", "Cancelled"]],
                "appraisal_cycle": current_cycle
            },
            fields=["name", "workflow_state", "employee"]
        )

        if not pending_appraisals:
            return

        # Group appraisals by manager; collect those with no eligible manager
        workflow = frappe.get_doc("Workflow", {"name": "Individual Appraisal"})
        state_roles = {state.state: state.allow_edit for state in workflow.states}
        manager_appraisals = {}
        unassigned = []
        for appraisal in pending_appraisals:
            doc = frappe.get_doc("Appraisal", appraisal.name)
            role = state_roles.get(doc.workflow_state)
            manager = get_manager_for_role(doc.employee, role) if role else None
            if manager:
                manager_appraisals.setdefault(manager, []).append(doc)
            else:
                unassigned.append(doc)

        # Skip managers already emailed today so a re-run only sends what is missing
        # Last run of the month: the 30th, or the 27th in February (no 30th)
        is_final = day == 30 or (today.month == 2 and day == 27)
        already_notified = get_managers_notified_today(today)
        for manager_user, appraisals in manager_appraisals.items():
            if manager_user in already_notified:
                continue
            send_summary_email(manager_user, appraisals, is_final)

        if unassigned:
            send_unassigned_alert(unassigned, today)

    except Exception as e:
        frappe.log_error(f"General error: {e}", "Appraisal Summary Notification Debug")


def get_managers_notified_today(today):
    """Return the set of users who already received a summary email today."""
    queued = frappe.get_all(
        "Email Queue",
        filters={
            "subject": ["like", "Action Required: % Pending Appraisal Approval(s)%"],
            "creation": [">", today],
        },
        pluck="name",
    )
    if not queued:
        return set()
    return set(
        frappe.get_all(
            "Email Queue Recipient",
            filters={"parent": ["in", queued]},
            pluck="recipient",
        )
    )


def send_unassigned_alert(appraisals, today):
    """
    Tell HR Managers about pending appraisals that have no eligible approver
    in the reports_to chain, so they are not silently skipped.
    """
    try:
        if frappe.db.exists(
            "Email Queue",
            {
                "subject": ["like", "Action Required: Pending Appraisals Without an Approver%"],
                "creation": [">", today],
            },
        ):
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
        for appraisal in appraisals:
            employee_name = frappe.db.get_value("Employee", appraisal.employee, "employee_name")
            url = frappe.utils.get_url_to_form("Appraisal", appraisal.name)
            rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{employee_name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{appraisal.workflow_state}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <a href="{url}">Open Appraisal</a>
                    </td>
                </tr>
            """

        message_table = f"""
            <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Employee</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Status</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        """

        for hr in hr_managers:
            frappe.sendmail(
                recipients=[hr["name"]],
                subject=f"Action Required: Pending Appraisals Without an Approver ({len(appraisals)})",
                message=f"""
                    Hello {hr['first_name']},<br><br>
                    The following pending appraisals have no eligible manager in the reporting line
                    (no enabled user with the required role), so no reminder could be sent.<br><br>
                    {message_table}
                    <br><br>
                    Please check the employees' Reports To setting.<br><br>
                    VF HR System
                """,
                now=True,
            )

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


def send_summary_email(manager_user, appraisals, is_final=False):
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

        # Subject must keep the "Action Required: ... Pending Appraisal Approval(s)"
        # shape: get_managers_notified_today matches on it.
        if is_final:
            subject = f"Action Required: {len(appraisals)} Pending Appraisal Approval(s) - FINAL REMINDER - {manager_name}"
            closing_line = (
                "<b>This is the final reminder for this cycle.</b> "
                "Please complete these appraisals today. "
                "Late scorecard submission will reflect on your own scorecard."
            )
        else:
            subject = f"Action Required: {len(appraisals)} Pending Appraisal Approval(s) - {manager_name}"
            closing_line = "Please complete these appraisals by the end of the month."

        frappe.sendmail(
            recipients=[manager_user],
            subject=subject,
            message=f"""
                Hello {manager_name},<br><br>
                You have {len(appraisals)} appraisal approval(s) pending your review.<br><br>
                {message_table}
                <br><br>
                {closing_line}<br><br>
                VF HR
            """,
            now=True
        )

    except Exception as e:
        frappe.log_error(f"Email error for {manager_user}: {e}", "Appraisal Summary Notification Debug")

