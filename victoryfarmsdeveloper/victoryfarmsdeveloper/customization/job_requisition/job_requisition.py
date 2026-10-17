# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _

REQUIRED_ROUNDS = (
	"Round 1: Talent Acquisition team",
	"Round 2: Hiring manager",
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


def _validate_contract_end_date(doc):
	employment_type = doc.get("custom_employment_type")
	if employment_type and employment_type != "Permanent" and not doc.get("custom_contract_end_date"):
		frappe.throw(
			_(
				"'If Not Permanent: Duration / End Date' is required when Employment Type is {0}."
			).format(employment_type)
		)
