from typing import Any

import frappe
from frappe.core.doctype.prepared_report import prepared_report
from frappe.desk import query_report
from frappe.desk.query_report import get_report_doc
from frappe.utils import add_to_date, now_datetime, sbool

VOUCHER_LEDGER = "General Ledger"


@frappe.whitelist()
@frappe.read_only()
def run(
	report_name,
	filters=None,
	user=None,
	ignore_prepared_report=False,
	custom_columns=None,
	is_tree=False,
	parent_field=None,
	are_default_filters=True,
):
	if sbool(ignore_prepared_report) and report_name == VOUCHER_LEDGER and not voucher_chosen(filters):
		ignore_prepared_report = False
	return query_report.run(
		report_name,
		filters=filters,
		ignore_prepared_report=ignore_prepared_report,
		custom_columns=custom_columns,
		is_tree=is_tree,
		parent_field=parent_field,
		are_default_filters=are_default_filters,
	)


def voucher_chosen(filters):
	return bool(frappe.parse_json(filters or {}).get("voucher_no"))


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
