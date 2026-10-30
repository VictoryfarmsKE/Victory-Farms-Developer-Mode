import frappe
from erpnext.accounts import utils
from frappe import _
from frappe.utils import cint
from frappe.utils.background_jobs import is_job_enqueued

RENAME_TIMEOUT = 3600


@frappe.whitelist()
def update_cost_center(docname, cost_center_name, cost_center_number, company, merge):
	frappe.has_permission("Cost Center", "write", doc=docname, throw=True)
	utils.validate_field_number("Cost Center", docname, cost_center_number, company, "cost_center_number")
	new_name = utils.get_autoname_with_number(cost_center_number, cost_center_name, company)
	if docname == new_name:
		return utils.update_cost_center(docname, cost_center_name, cost_center_number, company, merge)

	validate_target(new_name, cint(merge))
	job_id = rename_job_id(docname)
	if is_job_enqueued(job_id):
		frappe.throw(_("{0} is already being renamed. Please wait for it to finish.").format(frappe.bold(docname)))

	frappe.enqueue(
		rename_cost_center,
		queue="long",
		timeout=RENAME_TIMEOUT,
		job_id=job_id,
		enqueue_after_commit=True,
		docname=docname,
		cost_center_name=cost_center_name,
		cost_center_number=cost_center_number,
		company=company,
		merge=merge,
	)
	frappe.msgprint(
		_(
			"{0} is being renamed to {1} in the background. Past transactions are updated too, so this can take a few minutes. You will get a message when it is done."
		).format(frappe.bold(docname), frappe.bold(new_name)),
		title=_("Rename Queued"),
	)
	return docname


def validate_target(new_name, merge):
	exists = frappe.db.exists("Cost Center", new_name)
	if merge and not exists:
		frappe.throw(_("Cost Center {0} does not exist, select a new target to merge").format(new_name))
	if not merge and exists:
		frappe.throw(_("Another Cost Center with name {0} exists, select another name").format(new_name))


def rename_job_id(docname):
	return f"cost_center_rename::{docname}"


def rename_cost_center(docname, cost_center_name, cost_center_number, company, merge):
	try:
		new_name = utils.update_cost_center(docname, cost_center_name, cost_center_number, company, merge)
	except Exception:
		frappe.publish_realtime(
			"msgprint",
			_("Renaming {0} failed. Nothing was changed.").format(frappe.bold(docname)),
			user=frappe.session.user,
		)
		raise
	frappe.publish_realtime(
		"msgprint",
		_("{0} has been renamed to {1}.").format(frappe.bold(docname), frappe.bold(new_name or docname)),
		user=frappe.session.user,
	)
