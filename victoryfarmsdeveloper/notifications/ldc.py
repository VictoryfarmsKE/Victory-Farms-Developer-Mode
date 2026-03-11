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
    #get date of running cron (today) to estimate fiscal year, year starts in January
    year = target_date.year
    return str(year) if target_date.month >= 1 else str(year - 1)


def generate_quarterly_ldcs():
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
        fields=["name","department","reports_to"],
    )

    count = 0
    for emp in employees:
        exists = frappe.db.exists(
                "Leadership Development Card",
            {"employee": emp.name, "department": emp.department, "reports_to": emp.reports_to, "quarter": quarter_label, "year": fiscal_year },
        )
        if exists:
            continue

        create_ldc_for_employee(emp.name, emp.department, emp.reports_to,  quarter_label, fiscal_year)
        count += 1

def create_ldc_for_employee(employee: str, department: str, reports_to: str, quarter_label: str, fiscal_year: str):
    filters = {"employee": employee, "quarter": quarter_label}
    if fiscal_year:
        filters["year"] = fiscal_year

    if frappe.db.exists("Leadership Development Card", filters):
        frappe.log_error("A Leadership Development Card already exists for this employee and quarter. Please complete and submit it.")
        return
    try:
        ldc = frappe.new_doc("Leadership Development Card")
        ldc.employee = employee
        ldc.department = department
        ldc.reports_to = reports_to
        ldc.quarter = quarter_label
        ldc.year = fiscal_year
        ldc.flags.ignore_permissions = True
        ldc.insert()
        ldc.save()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "generate_quarterly_ldcs: create failed")
        return

    # Email 1:notify employee that LDC is available
    try:
        employee_user = frappe.db.get_value("Employee", employee, "user_id")
        employee_name = frappe.db.get_value("Employee", employee, "employee_name")
        if employee_user:
            ldc_link = get_url_to_form(ldc.doctype, ldc.name)
            month_end = formatdate(get_last_day(getdate()))
            message = (
                f"Hi {employee_name},<br><br>"
                f"Your Leadership Development Card (LDC) for this quarter has now been created in the system.<br><br>"
                f"Please complete your LDC before {month_end}.<br><br>"
                "The LDC is an opportunity to reflect on your performance, development progress, and priorities for the upcoming quarter.<br><br>"
                f'You can access your LDC here:<br><b><a href="{ldc_link}">{ldc_link}</a></b><br><br>Thank you.'
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
        recipients = []
        if employee_user:
            recipients.append(employee_user)

        try:
            url = get_url_to_form("Leadership Development Card", d.name)
            month_end = formatdate(get_last_day(getdate()))
            employee_name = frappe.db.get_value("Employee", d.employee, "employee_name")
            message = (
                f"Hi {employee_name},<br><br>"
                f"This is a reminder that your Leadership Development Card (LDC) for this quarter has not yet been completed.<br><br>"
                f"Please ensure your LDC is submitted before {month_end}.<br><br>"
                "You can access it here:<br>"
                f"<b><a href=\"{url}\">{d.name}</a></b><br><br>Thank you for your prompt attention to this."
            )
            frappe.sendmail(recipients=recipients, subject=f"Reminder: Leadership Development Card due by {month_end}.", message=message)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "send_ldc_reminders: email failed")


def notify_manager_on_submit(doc):
    """Notify manager when an employee submits their LDC."""
    manager_emp = doc.reports_to
    if not manager_emp:
        return

    manager_user = frappe.db.get_value("Employee", manager_emp, "user_id")
    try:
        url = get_url_to_form(doc.doctype, doc.name)
        manager_name = frappe.db.get_value("Employee", manager_emp, "employee_name")
        employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")
        message = (
            f"Hi {manager_name},<br><br>"
            f"{employee_name} has completed their Leadership Development Card (LDC) for this quarter and it is now ready for your review.<br><br>"
            "Please review ahead of your quarterly feedback conversation.<br><br>"
            "You can access the LDC here:<br>"
            f"<b><a href=\"{url}\">{doc.name}</a></b><br><br>Thank you."
        )
        if manager_user:
            frappe.sendmail(recipients=[manager_user], subject=f"Leadership Development Card Ready for Review – {employee_name}", message=message)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "notify_manager_on_submit: email failed")