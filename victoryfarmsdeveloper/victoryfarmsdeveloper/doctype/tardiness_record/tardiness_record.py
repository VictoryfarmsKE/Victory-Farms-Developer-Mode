# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt
import frappe
from datetime import timedelta
from frappe.utils import add_days, get_datetime, get_fullname, get_url_to_form, getdate, today
from frappe.model.document import Document


class TardinessRecord(Document):
	pass

def process_daily_attendance(process_date: str | None = None) -> dict[str, int | str]:
	attendance_date = getdate(process_date) if process_date else getdate(add_days(today(), -1))

	created_tardiness_records = _create_tardiness_records(attendance_date)
	created_leave_applications = _create_absence_leave_applications(attendance_date)

	return {
		"attendance_date": str(attendance_date),
		"tardiness_records_created": created_tardiness_records,
		"leave_applications_created": created_leave_applications,
	}


def send_monthly_hr_tardiness_report(reference_date: str | None = None) -> int:
	report_date = getdate(reference_date) if reference_date else getdate(today())
	period_start, period_end = _get_monthly_reporting_period(report_date)
	recipients = _get_hr_manager_recipients()

	if not recipients:
		return 0

	subject = (
		f"Monthly Tardiness Threshold Report - "
		f"{period_start.strftime('%b %d, %Y')} to {period_end.strftime('%b %d, %Y')}"
	)
	if _email_already_sent(subject, report_date):
		return 0

	rows = _get_tardiness_threshold_rows(period_start, period_end)
	if not rows:
		return 0

	message = _build_monthly_report_message(rows, period_start, period_end)
	for recipient in recipients:
		frappe.sendmail(
			recipients=[recipient["name"]],
			subject=subject,
			message=message.format(first_name=recipient["first_name"] or "HR Team"),
			now=False,
		)

	return len(rows)

UNPAID_LEAVE_TYPE = "Unpaid Leave"
TARDINESS_THRESHOLD = 5

def _create_tardiness_records(attendance_date) -> int:
	attendances = frappe.get_all(
		"Attendance",
		filters={
			"attendance_date": attendance_date,
			"late_entry": 1,
			"status": ["in", ["Present", "Half Day"]],
			"docstatus": 1,
		},
		fields=[
			"name",
			"employee",
			"employee_name",
			"attendance_date",
			"shift",
			"in_time",
		],
	)

	if not attendances:
		return 0

	existing_attendance_links = set(
		frappe.get_all(
			"Tardiness Record",
			filters={"attendance": ["in", [row.name for row in attendances]], "docstatus": ["!=", 2]},
			pluck="attendance",
		)
	)

	created_count = 0
	for attendance in attendances:
		if attendance.name in existing_attendance_links:
			continue

		actual_checkin_time = attendance.in_time or get_datetime(attendance.attendance_date)
		approver = frappe.db.get_value("Employee", attendance.employee, "leave_approver")
		tardiness_record = frappe.get_doc(
			{
				"doctype": "Tardiness Record",
				"employee": attendance.employee,
				"shift_type": attendance.shift,
				"attendance_date": attendance.attendance_date,
				"actual_checkin_time": actual_checkin_time,
				"attendance": attendance.name,
				"approver": approver,
				"approver_name": get_fullname(approver) if approver else None,
			}
		)
		tardiness_record.insert(ignore_permissions=True)
		created_count += 1
		_send_tardiness_notifications(tardiness_record)

	return created_count


def _create_absence_leave_applications(attendance_date) -> int:
	attendances = frappe.get_all(
		"Attendance",
		filters={
			"attendance_date": attendance_date,
			"status": "Absent",
			"docstatus": 1,
		},
		fields=["name", "employee", "employee_name", "attendance_date"],
	)

	created_count = 0
	for attendance in attendances:
		if _has_existing_leave_application(attendance.employee, attendance.attendance_date):
			continue

		leave_approver = frappe.db.get_value("Employee", attendance.employee, "leave_approver")
		leave_application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": attendance.employee,
				"leave_type": UNPAID_LEAVE_TYPE,
				"from_date": attendance.attendance_date,
				"to_date": attendance.attendance_date,
				"posting_date": attendance.attendance_date,
				"leave_approver": leave_approver,
				"leave_approver_name": get_fullname(leave_approver) if leave_approver else None,
				"description": (
					"Automatically created from Attendance "
					f"{attendance.name} for an absence on {attendance.attendance_date}."
				),
			}
		)
		leave_application.insert(ignore_permissions=True)
		created_count += 1

	return created_count


def _has_existing_leave_application(employee: str, attendance_date) -> bool:
	return bool(
		frappe.db.exists(
			"Leave Application",
			{
				"employee": employee,
				"docstatus": ["!=", 2],
				"from_date": ["<=", attendance_date],
				"to_date": [">=", attendance_date],
			},
		)
	)


def _send_tardiness_notifications(tardiness_record) -> None:
	url = get_url_to_form(tardiness_record.doctype, tardiness_record.name)
	employee_user = frappe.db.get_value("Employee", tardiness_record.employee, "user_id")
	if employee_user:
		frappe.sendmail(
			recipients=[employee_user],
			subject=f"Tardiness Recorded for {tardiness_record.attendance_date}",
			message=(
				f"Hello {tardiness_record.employee_name},<br><br>"
				f"A tardiness record has been created for your attendance on "
				f"<b>{tardiness_record.attendance_date}</b>. "
				f"Please add your reason on <a href=\"{url}\">{tardiness_record.name}</a>."
			),
			now=True,
		)

	if tardiness_record.approver:
		frappe.sendmail(
			recipients=[tardiness_record.approver],
			subject=f"Tardiness Pending Review for {tardiness_record.employee_name}",
			message=(
				f"Hello {tardiness_record.approver_name or 'Manager'},<br><br>"
				f"<a href=\"{url}\">{tardiness_record.name}</a> is pending your review for "
				f"{tardiness_record.employee_name} on <b>{tardiness_record.attendance_date}</b>."
			),
			now=True,
		)


def _get_monthly_reporting_period(reference_date) -> tuple:
	period_end = reference_date.replace(day=25)
	period_start = (period_end.replace(day=1) - timedelta(days=1)).replace(day=25)
	return period_start, period_end


def _get_tardiness_threshold_rows(period_start, period_end) -> list[dict]:
	return frappe.db.sql(
		"""
		SELECT
			tr.employee,
			MAX(tr.employee_name) AS employee_name,
			MAX(tr.department) AS department,
			COUNT(tr.name) AS tardy_count
		FROM `tabTardiness Record` tr
		WHERE tr.docstatus != 2
		AND tr.status == 'Rejected'
		AND tr.attendance_date >= %(period_start)s
		AND tr.attendance_date <= %(period_end)s
		GROUP BY tr.employee
		HAVING COUNT(tr.name) >= %(threshold)s
		ORDER BY tardy_count DESC, employee_name ASC
		""",
		{
			"period_start": period_start,
			"period_end": period_end,
			"threshold": TARDINESS_THRESHOLD,
		},
		as_dict=True,
	)


def _build_monthly_report_message(rows: list[dict], period_start, period_end) -> str:
	row_html = "".join(
		f"""
		<tr>
			<td style=\"padding:6px 10px;border:1px solid #ddd;\">{row['employee']}</td>
			<td style=\"padding:6px 10px;border:1px solid #ddd;\">{row['employee_name']}</td>
			<td style=\"padding:6px 10px;border:1px solid #ddd;\">{row.get('department') or ''}</td>
			<td style=\"padding:6px 10px;border:1px solid #ddd;text-align:right;\">{row['tardy_count']}</td>
		</tr>
		"""
		for row in rows
	)

	return f"""
		Hello {{first_name}},<br><br>
		The following employees reached the tardiness threshold of <b>{TARDINESS_THRESHOLD}+</b>
		between <b>{period_start.strftime('%B %d, %Y')}</b> and <b>{period_end.strftime('%B %d, %Y')}</b>.<br><br>
		<table style=\"border-collapse:collapse;font-family:Arial, sans-serif;font-size:13px;\">
			<thead>
				<tr style=\"background:#f2f2f2;\">
					<th style=\"padding:6px 10px;border:1px solid #ddd;\">Employee ID</th>
					<th style=\"padding:6px 10px;border:1px solid #ddd;\">Employee</th>
					<th style=\"padding:6px 10px;border:1px solid #ddd;\">Department</th>
					<th style=\"padding:6px 10px;border:1px solid #ddd;\">Tardy Count</th>
				</tr>
			</thead>
			<tbody>
				{row_html}
			</tbody>
		</table>
		<br><br>
	"""


def _get_hr_manager_recipients() -> list[dict]:
	return frappe.db.sql(
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


def _email_already_sent(subject: str, reference_date) -> bool:
	day_start = get_datetime(reference_date)
	day_end = day_start + timedelta(days=1)
	return bool(
		frappe.db.exists(
			"Email Queue",
			{
				"subject": subject,
				"creation": ["between", [day_start, day_end]],
			},
		)
	)
