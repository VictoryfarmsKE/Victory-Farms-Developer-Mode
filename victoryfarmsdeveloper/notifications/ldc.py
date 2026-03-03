import frappe
from frappe.utils import get_url_to_form, get_last_day, getdate, formatdate
from frappe.utils.data import get_quarter_start, get_quarter_ending
from datetime import date


def _get_quarter_label(target_date: date) -> str:
    q_start = get_quarter_start(target_date)
    q_end = get_quarter_ending(target_date)
    month = q_start.month
    if month in (1, 2, 3):
        return "Q1"
    if month in (4, 5, 6):
        return "Q2"
    if month in (7, 8, 9):
        return "Q3"
    return "Q4"


def _get_fiscal_year_for_date(target_date: date) -> str | None:
    fiscal = frappe.db.get_value(
        "Fiscal Year",
        filters={"year_start_date": ["<=", target_date], "year_end_date": [">=", target_date]},
    )
    return fiscal


def generate_quarterly_ldcs(publish_progress: bool = False):
    """Create Draft Leadership Development Cards for active employees whose
    `custom_appraisal_template` contains 'M/D/C' for the current quarter.
    Trigged by cron on 15th of Mar/Jun/Sep/Dec.
    """
    target_date = frappe.utils.getdate()
    quarter_label = _get_quarter_label(target_date)
    fiscal_year = _get_fiscal_year_for_date(target_date)
    

    #fetch active employees matching template pattern
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active", "custom_appraisal_template": ["like", "%M/D/C%"]},
        fields=["name"],
    )

    count = 0
    for emp in employees:
        exists = frappe.db.exists(
            "Leadership Development Card",
            {"employee": emp.name, "quarter": quarter_label, "year": fiscal_year },
        )
        print(f"Checking LDC for {emp.name} - exists: {exists}", quarter_label, fiscal_year)
        if exists:
            continue

        create_ldc_for_employee(emp.name, quarter_label, fiscal_year)
        count += 1

        if publish_progress and employees:
            frappe.publish_progress(count * 100 / len(employees), title="Creating LDCs...")


def create_ldc_for_employee(employee: str, quarter_label: str, fiscal_year: str):
    doc = frappe.get_doc(
        {
            "doctype": "Leadership Development Card",
            "employee": employee,
            "quarter": quarter_label,
            "year": fiscal_year,
        }
    )
    doc.flags.ignore_permissions = True
    try:
        doc.insert()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "generate_quarterly_ldcs: create failed")
    else:
        # Email 1: notify employee that LDC is available
        try:
            employee_user = frappe.db.get_value("Employee", employee, "user_id")
            employee_name = frappe.db.get_value("Employee", employee, "employee_name")
            if employee_user:
                ldc_link = get_url_to_form(doc.doctype, doc.name)
                month_end = formatdate(get_last_day(getdate()))
                message = (
                    f"Hi {employee_name},\n\n"
                    f"Your Leadership Development Card (LDC) for this quarter has now been created in the system.\n\n"
                    f"Please complete your LDC before {month_end}.\n\n"
                    "The LDC is an opportunity to reflect on your performance, development progress, and priorities for the upcoming quarter.\n\n"
                    f"You can access your LDC here:\n{ldc_link}\n\nThank you."
                )
                frappe.sendmail(recipients=[employee_user], subject="Action Required - Leadership Development Card Now Available", message=message)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "create_ldc_for_employee: notification failed")


def send_ldc_reminders():
    """Send reminder emails for draft LDCs for the current quarter."""
    target_date = frappe.utils.getdate()
    quarter_label = _get_quarter_label(target_date)
    fiscal_year = _get_fiscal_year_for_date(target_date)

    drafts = frappe.get_all(
        "Leadership Development Card",
        filters={"quarter": quarter_label, "year": fiscal_year, "docstatus": 0},
        fields=["name", "employee", "reports_to"],
    )

    for d in drafts:
        employee_user = frappe.db.get_value("Employee", d.employee, "user_id")
        manager_user = None
        if d.reports_to:
            manager_user = frappe.db.get_value("Employee", d.reports_to, "user_id")

        recipients = []
        if employee_user:
            recipients.append(employee_user)

        try:
            url = get_url_to_form("Leadership Development Card", d.name)
            month_end = formatdate(get_last_day(getdate()))
            employee_name = frappe.db.get_value("Employee", d.employee, "employee_name")
            message = (
                f"Hi {employee_name},\n\n"
                f"This is a reminder that your Leadership Development Card (LDC) for this quarter has not yet been completed.\n\n"
                f"Please ensure your LDC is submitted before {month_end}.\n\n"
                "You can access it here:\n"
                f"{url}\n\nThank you for your prompt attention to this."
            )
            # send to employee; copy manager if available
            frappe.sendmail(recipients=recipients, subject=f"Reminder: Leadership Development Card due by {month_end}.", message=message, cc=([manager_user] if manager_user else None))
        except Exception:
            frappe.log_error(frappe.get_traceback(), "send_ldc_reminders: email failed")


def notify_manager_on_submit(doc):
    """Notify manager when an employee submits their LDC."""
    manager_emp = doc.reports_to
    if not manager_emp:
        return

    manager_user = frappe.db.get_value("Employee", manager_emp, "user_id")
    employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    try:
        url = get_url_to_form(doc.doctype, doc.name)
        manager_name = frappe.db.get_value("Employee", manager_emp, "employee_name")
        employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")
        message = (
            f"Hi {manager_name},\n\n"
            f"{employee_name} has completed their Leadership Development Card (LDC) for this quarter and it is now ready for your review.\n\n"
            "Please review ahead of your quarterly feedback conversation.\n\n"
            "You can access the LDC here:\n"
            f"{url}\n\nThank you."
        )
        if manager_user:
            frappe.sendmail(recipients=[manager_user], subject=f"Leadership Development Card Ready for Review – {employee_name}", message=message, cc=[employee_user] if employee_user else None)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "notify_manager_on_submit: email failed")
