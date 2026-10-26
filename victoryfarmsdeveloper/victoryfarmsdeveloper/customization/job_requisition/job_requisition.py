# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _

REQUIRED_ROUNDS = (
	"Round 1: Talent Acquisition team",
	"Round 2: Hiring manager",
)


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
def get_department_heads(doctype, txt, searchfield, start, page_len, filters):
	"""Return all employees who are set as department heads (for Link query)."""
	heads = frappe.get_all(
		"Department",
		filters={"department_head": ("is", "set")},
		pluck="department_head",
	)
	if not heads:
		return []

	search_txt = f"%{txt}%" if txt else "%"
	return frappe.db.sql(
		"""
		SELECT name, employee_name, designation
		FROM tabEmployee
		WHERE name IN %(heads)s
		  AND status = 'Active'
		  AND (name LIKE %(txt)s OR employee_name LIKE %(txt)s)
		ORDER BY employee_name
		LIMIT %(start)s, %(page_len)s
		""",
		{"heads": heads, "txt": search_txt, "start": int(start), "page_len": int(page_len)},
		as_list=1,
	)


@frappe.whitelist()
def has_hiring_manager_designation():
	"""Return True if at least one active employee has the Hiring Manager designation."""
	return frappe.db.exists(
		"Employee", {"designation": "Hiring Manager", "status": "Active"}
	)


def validate_job_requisition(doc, method=None):
	"""Server-side enforcement of the VF Job Requisition Form rules.

	Mirrors the paper template:
	- Section D: a requisition without a JD is returned.
	- Section E: interview rounds 1 and 2 must be named before submission.
	- Section A: non-permanent roles must state duration / end date.
	"""
	_validate_job_description(doc)
	_validate_interviewers(doc)
	_validate_availability_dates(doc)
	_validate_contract_end_date(doc)


def _validate_job_description(doc):
	if not doc.get("custom_jd_attached"):
		frappe.throw(
			_(
				"Job description is mandatory: requisitions without a JD are returned. "
				"Please attach the JD and tick 'Job Description Attached' in Section D."
			)
		)
	if not doc.get("custom_jd_attachment"):
		frappe.throw(
			_("Please upload the job description file (Section D: Job Description Attachment).")
		)


def _validate_interviewers(doc):
	rows = doc.get("custom_interviewers") or []
	rounds = {(row.get("interview_round") or "").strip() for row in rows}

	missing = [r for r in REQUIRED_ROUNDS if r not in rounds]
	if missing:
		frappe.throw(
			_("Interview rounds 1 and 2 must be named before submission. Missing: {0}").format(
				", ".join(missing)
			)
		)

	for row in rows:
		if not (row.get("interviewer_name") or "").strip():
			frappe.throw(
				_("Interviewer name is required for {0}.").format(row.get("interview_round"))
			)


def _validate_availability_dates(doc):
	availability = doc.get("custom_hm_availability") or []
	if not availability:
		frappe.throw(_("Please add at least one hiring manager availability date in Section E."))


def _validate_contract_end_date(doc):
	employment_type = doc.get("custom_employment_type")
	if employment_type and employment_type != "Permanent" and not doc.get("custom_contract_end_date"):
		frappe.throw(
			_(
				"'If Not Permanent: Duration / End Date' is required when Employment Type is {0}."
			).format(employment_type)
		)
