import hashlib
import inspect
import json

import frappe
from erpnext.accounts.doctype.pos_invoice_merge_log import pos_invoice_merge_log as merge_log
from frappe.utils import get_time, getdate, nowdate, nowtime

EXPECTED_SOURCE_SHA256 = "89e4a07111201a96fc1e1bb83c5ad3a82d574f860091755dfbd4bda17f49ef95"
original_create_merge_logs = merge_log.create_merge_logs


def watched_sources():
	return (merge_log.consolidate_pos_invoices, original_create_merge_logs)


def create_merge_logs(invoice_by_customer, closing_entry=None):
	try:
		for customer, invoices_acc_dim in invoice_by_customer.items():
			for invoices in invoices_acc_dim.values():
				for _invoices in merge_log.split_invoices(invoices):
					pending = not_yet_consolidated(_invoices)
					if not pending:
						continue
					log = frappe.new_doc("POS Invoice Merge Log")
					log.posting_date = getdate(closing_entry.get("posting_date")) if closing_entry else nowdate()
					log.posting_time = get_time(closing_entry.get("posting_time")) if closing_entry else nowtime()
					log.company = closing_entry.get("company") if closing_entry else None
					log.customer = customer
					log.pos_closing_entry = closing_entry.get("name") if closing_entry else None
					log.set("pos_invoices", pending)
					log.save(ignore_permissions=True)
					log.submit()
					frappe.db.commit()
		if closing_entry:
			closing_entry.set_status(update=True, status="Submitted")
			closing_entry.db_set("error_message", "")
			closing_entry.update_opening_entry()

	except Exception as e:
		frappe.db.rollback()
		message_log = frappe.message_log.pop() if frappe.message_log else str(e)
		error_message = merge_log.get_error_message(message_log)

		if closing_entry:
			closing_entry.set_status(update=True, status="Failed")
			if isinstance(error_message, list):
				error_message = json.dumps(error_message)
			closing_entry.db_set("error_message", error_message)
		raise

	finally:
		frappe.db.commit()
		frappe.publish_realtime("closing_process_complete", user=frappe.session.user)


def not_yet_consolidated(invoices):
	names = [d.pos_invoice for d in invoices]
	consolidated = set(
		frappe.get_all(
			"POS Invoice", filters={"name": ("in", names), "status": "Consolidated"}, pluck="name"
		)
	)
	return [d for d in invoices if d.pos_invoice not in consolidated]


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
	merge_log.create_merge_logs = create_merge_logs


def is_installed():
	return merge_log.create_merge_logs is create_merge_logs


def check():
	install()
	if is_installed():
		return []
	problems = ["ERPNext POS closing changed, closings hold the Sales Invoice number until the end again"]
	frappe.log_error(title="POS closing commit check failed", message="\n".join(problems))
	return problems
