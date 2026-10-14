import hashlib
import inspect

import frappe
from frappe.core.doctype.prepared_report import prepared_report
from frappe.utils.background_jobs import enqueue

EXPECTED_SOURCE_SHA256 = "1a8a393d8f71782991c1a2b799248f40d9e9dfd8680f3b8e84c3a715041dd299"
QUICK_REPORTS = ("POS Invoice Daily Sales", "Victory Farms Daily Sales")
QUICK_QUEUE = "short"
QUICK_TIMEOUT = 300
original_after_insert = prepared_report.PreparedReport.after_insert


def after_insert(self):
	if self.report_name not in QUICK_REPORTS:
		return original_after_insert(self)
	enqueue(
		prepared_report.generate_report,
		queue=QUICK_QUEUE,
		prepared_report=self.name,
		timeout=QUICK_TIMEOUT,
		enqueue_after_commit=True,
	)


def source_matches():
	try:
		source = inspect.getsource(original_after_insert)
	except (OSError, TypeError):
		return False
	return hashlib.sha256(source.encode()).hexdigest() == EXPECTED_SOURCE_SHA256


def install():
	if not source_matches():
		return
	prepared_report.PreparedReport.after_insert = after_insert


def is_installed():
	return prepared_report.PreparedReport.after_insert is after_insert


def check():
	install()
	if is_installed():
		return []
	problems = ["Frappe prepared report queueing changed, quick sales reports wait behind heavy reports again"]
	frappe.log_error(title="Quick report queue check failed", message="\n".join(problems))
	return problems
