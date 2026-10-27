# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_url_to_form

MANDATORY_ROUND = "Round 2: Hiring manager"

TA_TEAM_ROLE = "HR User"

# Fixed budget amounts by Employee Grade (KES). Grades not listed are treated
# as flexible / "Not Set" and the user enters the budget manually.
GRADE_BUDGET_MAP = {
	# C grades
	"C10H": 30150,
	"C10M": 30150,
	"C1H": 11250,
	"C1M": 11250,
	"C2H": 12825,
	"C2M": 12825,
	"C3H": 13725,
	"C3M": 13725,
	"C4H": 14850,
	"C4M": 14850,
	"C5H": 17100,
	"C5M": 17100,
	"C6H": 18900,
	"C6M": 18900,
	"C7H": 21600,
	"C7M": 21600,
	"C8H": 24300,
	"C8M": 24300,
	"C9H": 27225,
	"C9M": 27225,
	# F grades
	"F10H": 43425,
	"F10M": 43425,
	"F11H": 45697.5,
	"F11M": 45697.5,
	"F12H": 47835,
	"F12M": 47835,
	"F13H": 50085,
	"F13M": 50085,
	"F14H": 52447.5,
	"F14M": 52447.5,
	"F15H": 54922.5,
	"F15M": 54922.5,
	"F1H": 19350,
	"F1M": 19350,
	"F2H": 21825,
	"F2M": 21825,
	"F3H": 24525,
	"F3M": 24525,
	"F4H": 27000,
	"F4M": 27000,
	"F5H": 29925,
	"F5M": 29925,
	"F6H": 32625,
	"F6M": 32625,
	"F7H": 35550,
	"F7M": 35550,
	"F8H": 37800,
	"F8M": 37800,
	"F9H": 40500,
	"F9M": 40500,
	# L grades
	"L10H": 30600,
	"L10M": 30600,
	"L11H": 32265,
	"L11M": 32265,
	"L12H": 33772.5,
	"L12M": 33772.5,
	"L13H": 35347.5,
	"L13M": 35347.5,
	"L14H": 37012.5,
	"L14M": 37012.5,
	"L15H": 38745,
	"L15M": 38745,
	"L1H": 11700,
	"L1M": 11700,
	"L2H": 13275,
	"L2M": 13275,
	"L3H": 14175,
	"L3M": 14175,
	"L4H": 15300,
	"L4M": 15300,
	"L5H": 17550,
	"L5M": 17550,
	"L6H": 19350,
	"L6M": 19350,
	"L7H": 22050,
	"L7M": 22050,
	"L8H": 24750,
	"L8M": 24750,
	"L9H": 27450,
	"L9M": 27450,
	# P grades
	"P1": 9450,
	"P2": 9900,
	"P3": 10350,
	"P4": 10800,
	"P5": 11250,
	# S grades
	"S1": 40000,
	"S2": 43200,
	"S3": 46500,
	"S4": 51900,
	"S5": 58700,
	"S6": 65000,
	"S7": 71600,
	"S8": 80500,
	"S9": 89100,
	"S10": 102200,
}


@frappe.whitelist()
def get_current_employee():
	"""Return the Employee record linked to the logged-in user, if any.

	Matches on Employee.user_id == the current session user. Runs with
	ignore_permissions because a requester only needs to resolve their own
	identity, not browse the Employee list.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return {}

	employee = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "employee_name"],
		as_dict=True,
	)
	if not employee:
		# Fall back to any status in case the employee record hasn't been
		# marked Active yet, rather than leaving the requester with nothing.
		employee = frappe.db.get_value(
			"Employee",
			{"user_id": user},
			["name", "employee_name"],
			as_dict=True,
		)

	if not employee:
		return {}

	return {"name": employee.name, "employee_name": employee.employee_name}


@frappe.whitelist()
def get_employee_details(employee):
	"""Return job title and contact info for the selected employee."""
	if not employee:
		return {}
	emp = frappe.db.get_value(
		"Employee",
		employee,
		["designation", "user_id", "cell_number", "prefered_email", "company_email"],
		as_dict=True,
	)
	if not emp:
		return {}

	email = emp.prefered_email or emp.company_email or emp.user_id or ""
	phone = emp.cell_number or ""
	return {
		"job_title": emp.designation or "",
		"email_phone": email or phone,
	}


@frappe.whitelist()
def get_grade_budget_mapping(grade):
	"""Return the budget type and amount for the selected Employee Grade."""
	if not grade:
		return {"budget_type": "Flexible", "fixed_amount": 0}
	fixed_amount = GRADE_BUDGET_MAP.get(grade)
	if fixed_amount:
		return {"budget_type": "Fixed", "fixed_amount": fixed_amount}
	return {"budget_type": "Flexible", "fixed_amount": 0}


def validate_job_requisition(doc, method=None):
	"""Server-side enforcement of the VF Job Requisition Form rules."""
	_validate_job_description(doc)
	_validate_interviewers(doc)
	_validate_budget(doc)


def _validate_job_description(doc):
	if not doc.get("custom_jd_attachment"):
		frappe.throw(
			_("Please upload the job description file (Section D: Job Description Attachment).")
		)


def _validate_interviewers(doc):
	rows = doc.get("custom_interviewers") or []
	round2_rows = [row for row in rows if row.get("interview_round") == MANDATORY_ROUND]

	if not round2_rows or not (round2_rows[0].get("interviewer_name") or "").strip():
		frappe.throw(_("Round 2 (Hiring Manager) interviewer is required before submission."))


def _validate_budget(doc):
	grade = doc.get("custom_budget_grid_level")
	if not grade:
		return

	if grade in GRADE_BUDGET_MAP:
		expected = GRADE_BUDGET_MAP[grade]
		amount = doc.get("custom_budget_amount") or 0
		if amount and amount != expected:
			frappe.msgprint(
				_(
					"Budget amount for {0} should normally be {1} KES. Please confirm if different."
				).format(grade, expected),
				indicator="orange",
				alert=True,
			)


def on_update_job_requisition(doc, method=None):
	"""Send approval-workflow emails when workflow_state changes.

	- Draft -> Pending Department Head Approval: notify the named Department Head.
	- -> Approved / Rejected: notify the TA team (HR User role), including the
	  rejection reason when applicable.

	Email delivery failures (e.g. no outgoing Email Account configured) are
	caught and logged rather than raised, so a broken mail setup never blocks
	the workflow transition itself.
	"""
	previous = doc.get_doc_before_save()
	previous_state = previous.workflow_state if previous else None
	current_state = doc.workflow_state

	if previous_state == current_state:
		return

	try:
		if current_state == "Pending Department Head Approval":
			_notify_department_head(doc)
		elif current_state in ("Approved", "Rejected"):
			_notify_ta_team(doc, current_state)
	except Exception:
		frappe.log_error(
			title="Job Requisition: notification email failed",
			message=frappe.get_traceback(),
		)


def _requester_display_name(doc):
	return (
		doc.get("requested_by_name")
		or frappe.db.get_value("Employee", doc.get("requested_by"), "employee_name")
		or doc.get("requested_by")
		or doc.owner
	)


def _notify_department_head(doc):
	dept_head = doc.get("custom_dept_head_name")
	if not dept_head:
		frappe.log_error(
			title="Job Requisition: missing Department Head",
			message=f"{doc.name} was submitted without a Department Head selected; no approval email sent.",
		)
		return

	user = frappe.db.get_value("Employee", dept_head, "user_id")
	if not user:
		frappe.log_error(
			title="Job Requisition: Department Head has no linked User",
			message=(
				f"{doc.name}: Department Head {dept_head} has no User ID on their Employee "
				"record, so the approval email could not be sent."
			),
		)
		return

	dept_head_name = frappe.db.get_value("Employee", dept_head, "employee_name") or dept_head
	position_title = doc.get("custom_job_position_title") or doc.name
	link = get_url_to_form(doc.doctype, doc.name)

	subject = _("Action Required: Job Requisition Approval - {0}").format(position_title)
	message = f"""
		<p>{_("Good day")} {dept_head_name},</p>
		<p>{_("A new job requisition for")} <strong>{position_title}</strong>
		{_("has been submitted by")} {_requester_display_name(doc)} {_("and requires your approval.")}</p>
		<p>{_("Please click the link below to review and take action:")}</p>
		<p><a href="{link}">{_("Review Job Requisition")}</a></p>
		<p>{_("You will be able to Approve or Reject this request. If rejecting, please provide a reason so the requester can revise and resubmit.")}</p>
	"""

	frappe.sendmail(recipients=[user], subject=subject, message=message)


def _notify_ta_team(doc, state):
	user_names = frappe.get_all(
		"Has Role", filters={"role": TA_TEAM_ROLE, "parenttype": "User"}, pluck="parent"
	)
	if not user_names:
		return

	recipients = frappe.get_all(
		"User",
		filters={"name": ("in", user_names), "enabled": 1},
		pluck="name",
	)
	if not recipients:
		return

	position_title = doc.get("custom_job_position_title") or doc.name
	link = get_url_to_form(doc.doctype, doc.name)
	state_label = _("Approved") if state == "Approved" else _("Rejected")

	reason_html = ""
	if state == "Rejected" and doc.get("custom_rejection_reason"):
		reason_html = f"<p><strong>{_('Reason for rejection')}:</strong> {doc.get('custom_rejection_reason')}</p>"

	subject = _("Job Requisition {0}: {1}").format(state_label, position_title)
	message = f"""
		<p>{_("The job requisition")} <strong>{position_title}</strong> {_("has been")}
		<strong>{state_label}</strong> {_("by the Department Head")}.</p>
		{reason_html}
		<p><a href="{link}">{_("View Job Requisition")}</a></p>
	"""

	frappe.sendmail(recipients=recipients, subject=subject, message=message)
