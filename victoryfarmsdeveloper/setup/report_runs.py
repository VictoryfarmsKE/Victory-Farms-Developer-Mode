from typing import Any

import frappe
from frappe.core.doctype.prepared_report import prepared_report
from frappe.desk.query_report import get_report_doc
from frappe.utils import add_to_date, now_datetime


@frappe.whitelist()
def make_prepared_report(report_name: str, filters: dict[str, Any] | str | list | None = None):
	get_report_doc(report_name)
	running = running_report(report_name, filters)
	if running:
		return {"name": running}
	return prepared_report.make_prepared_report(report_name, filters)


def running_report(report_name, filters):
	timeout = frappe.get_value("Report", report_name, "timeout") or prepared_report.REPORT_TIMEOUT
	return frappe.db.get_value(
		"Prepared Report",
		{
			"report_name": report_name,
			"owner": frappe.session.user,
			"status": ("in", ("Queued", "Started")),
			"filters": prepared_report.process_filters_for_prepared_report(filters),
			"creation": (">", add_to_date(now_datetime(), seconds=-timeout)),
		},
		"name",
		order_by="creation desc",
	)
