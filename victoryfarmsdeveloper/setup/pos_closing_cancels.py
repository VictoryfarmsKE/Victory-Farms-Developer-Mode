import hashlib
import inspect

import frappe
from erpnext.accounts.doctype.pos_closing_entry import pos_closing_entry
from erpnext.accounts.doctype.pos_invoice_merge_log import pos_invoice_merge_log as merge_log
from frappe import _
from frappe.utils import getdate, now_datetime
from frappe.utils.background_jobs import enqueue, is_job_enqueued

EXPECTED_SOURCE_SHA256 = "106fea33558a86bb5fa5237a16da4f5a50ff57cc5497bc20672bbeb9a9930a01"
LARGE_CANCEL_LOGS = 10
TRADING_HOURS = range(6, 21)
original_unconsolidate_pos_invoices = merge_log.unconsolidate_pos_invoices


def watched_sources():
	return (
		merge_log.enqueue_job,
		merge_log.unconsolidate_pos_invoices,
		merge_log.cancel_merge_logs,
		pos_closing_entry.POSClosingEntry.on_cancel,
	)


def enqueue_job(job, **kwargs):
	merge_log.check_scheduler_status()

	closing_entry = kwargs.get("closing_entry") or {}

	job_id = "pos_invoice_merge::" + str(closing_entry.get("name"))
	if not is_job_enqueued(job_id):
		enqueue(
			job,
			**kwargs,
			queue="long",
			timeout=10000,
			event="processing_merge_logs",
			job_id=job_id,
			now=frappe.conf.developer_mode or frappe.flags.in_test,
			enqueue_after_commit=True,
		)

		if job == merge_log.create_merge_logs:
			msg = _("POS Invoices will be consolidated in a background process")
		else:
			msg = _("POS Invoices will be unconsolidated in a background process")

		frappe.msgprint(msg, alert=1)


def unconsolidate_pos_invoices(closing_entry):
	if should_wait_for_evening(closing_entry):
		closing_entry.set_status(update=True, status="Queued")
		frappe.msgprint(
			_(
				"This closing has many merged invoices and is not from today, so they will be unconsolidated after {0}:00 tonight"
			).format(TRADING_HOURS.stop),
			alert=1,
		)
		return
	return original_unconsolidate_pos_invoices(closing_entry)


def should_wait_for_evening(closing_entry):
	if now_datetime().hour not in TRADING_HOURS:
		return False
	if getdate(closing_entry.period_end_date) >= getdate(now_datetime()):
		return False
	return frappe.db.count("POS Invoice Merge Log", {"pos_closing_entry": closing_entry.name}) >= LARGE_CANCEL_LOGS


def run_held_cancels():
	for name in frappe.get_all(
		"POS Closing Entry", filters={"docstatus": 2, "status": "Queued"}, pluck="name", order_by="modified"
	):
		closing_entry = frappe.get_doc("POS Closing Entry", name)
		merge_logs = frappe.get_all(
			"POS Invoice Merge Log", filters={"pos_closing_entry": name, "docstatus": 1}, pluck="name"
		)
		merge_log.enqueue_job(merge_log.cancel_merge_logs, merge_logs=merge_logs, closing_entry=closing_entry)


def source_sha256():
	source = "".join(inspect.getsource(fn) for fn in watched_sources())
	return hashlib.sha256(source.encode()).hexdigest()


def source_matches():
	try:
		return source_sha256() == EXPECTED_SOURCE_SHA256
	except (OSError, TypeError):
		return False


def install():
	if not source_matches():
		return
	merge_log.enqueue_job = enqueue_job
	merge_log.unconsolidate_pos_invoices = unconsolidate_pos_invoices
	pos_closing_entry.unconsolidate_pos_invoices = unconsolidate_pos_invoices


def is_installed():
	return (
		merge_log.enqueue_job is enqueue_job
		and merge_log.unconsolidate_pos_invoices is unconsolidate_pos_invoices
		and pos_closing_entry.unconsolidate_pos_invoices is unconsolidate_pos_invoices
	)


def check():
	install()
	if is_installed():
		return []
	problems = ["ERPNext POS closing cancel changed, large cancels run during trading hours again"]
	frappe.log_error(title="POS closing cancel check failed", message="\n".join(problems))
	return problems
