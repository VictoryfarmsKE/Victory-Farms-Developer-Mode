import hashlib
import json

import frappe
from frappe import _
from frappe.core.doctype.prepared_report.prepared_report import (
	get_completed_prepared_report,
	process_filters_for_prepared_report,
)
from frappe.desk import query_report
from frappe.desk.reportview import clean_params, parse_json
from frappe.desk.utils import pop_csv_params
from frappe.utils import add_to_date, cint, now, now_datetime

from victoryfarmsdeveloper.setup import report_runs

CACHE_KEY = "vf_background_export_reports"
ROWS_CACHE_KEY = "vf_prepared_report_rows"
REPEAT_CLICK_SECONDS = 60
WAITING = "Waiting for Report"
QUEUED = "Queued"
SENT = "Sent"
FAILED = "Failed"
RUNNING = ("Queued", "Started")


def background_reports():
	reports = frappe.cache.get_value(CACHE_KEY)
	if reports is None:
		reports = frappe.get_all(
			"Background Export Report",
			filters={"parenttype": "Report Export Settings"},
			pluck="report",
		)
		frappe.cache.set_value(CACHE_KEY, reports)
	return reports


def clear_background_reports():
	frappe.cache.delete_value(CACHE_KEY)


@frappe.whitelist()
def get_background_reports():
	return background_reports()


def screen_row_limit():
	return cint(frappe.defaults.get_global_default("max_report_rows")) or 100000


def result_rows(prepared_report):
	key = f"{ROWS_CACHE_KEY}:{prepared_report}"
	rows = frappe.cache.get_value(key)
	if rows is None:
		data = json.loads(frappe.get_doc("Prepared Report", prepared_report).get_prepared_data().decode("utf-8"))
		rows = len(data.get("result") or []) if isinstance(data, dict) else len(data)
		frappe.cache.set_value(key, rows, expires_in_sec=86400)
	return rows


@frappe.whitelist()
def export_mode(report_name, filters=None, custom_columns=None):
	if report_name not in background_reports():
		return "download"
	frappe.permissions.can_export(
		frappe.get_cached_value("Report", report_name, "ref_doctype"),
		raise_exception=True,
	)
	filters = dict(frappe.parse_json(filters) or {})
	chosen = filters.pop("prepared_report_name", None)
	report = query_report.get_report_doc(report_name)
	if not report.prepared_report or frappe.parse_json(custom_columns or "[]"):
		return "background"
	if chosen:
		frappe.has_permission("Prepared Report", "read", chosen, throw=True)
	elif report_runs.running_report(report_name, filters):
		return "background"
	name = chosen or get_completed_prepared_report(filters, frappe.session.user, report_name)
	if not name or frappe.db.get_value("Prepared Report", name, "status") != "Completed":
		return "background"
	return "download" if result_rows(name) <= screen_row_limit() else "background"


@frappe.whitelist()
def export_query():
	form_dict = frappe.local.form_dict
	if form_dict.report_name not in background_reports():
		return query_report.export_query()
	if not cint(form_dict.export_in_background) and export_mode(form_dict.report_name, form_dict.filters, form_dict.custom_columns) == "download":
		return query_report.export_query()

	form_params = frappe._dict(frappe.local.form_dict)
	csv_params = pop_csv_params(form_params)
	clean_params(form_params)
	parse_json(form_params)
	form_params.pop("export_in_background", None)

	report_name = form_params.report_name
	frappe.permissions.can_export(
		frappe.get_cached_value("Report", report_name, "ref_doctype"),
		raise_exception=True,
	)
	report = query_report.get_report_doc(report_name)
	user = frappe.session.user
	user_email = frappe.get_cached_value("User", user, "email")
	filters = form_params.filters or {}
	chosen = filters.pop("prepared_report_name", None)
	key = request_key(report_name, filters, form_params.file_format_type, form_params.custom_columns)

	if repeat_click(user, key):
		frappe.msgprint(
			_("This export is already on its way. You will receive an email on {0} with a download link once it is ready.").format(user_email)
		)
		return

	prepared = report.prepared_report and not frappe.parse_json(form_params.custom_columns or "[]")
	name = None
	if prepared:
		if chosen:
			frappe.has_permission("Prepared Report", "read", chosen, throw=True)
		name = chosen or report_runs.running_report(report_name, filters)
		if not name:
			name = get_completed_prepared_report(filters, user, report_name)
			if not name:
				name = report_runs.make_prepared_report(report_name, filters)["name"]
		filters["prepared_report_name"] = name
	form_params.filters = filters

	if prepared and frappe.db.get_value("Prepared Report", name, "status") in RUNNING:
		form_params.visible_idx = []

	request = frappe.get_doc(
		{
			"doctype": "Report Export Request",
			"report_name": report_name,
			"user": user,
			"file_format": form_params.file_format_type,
			"status": WAITING,
			"prepared_report": name,
			"request_key": key,
			"form_params": frappe.as_json(form_params),
			"csv_params": frappe.as_json(csv_params),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	status = frappe.db.get_value("Prepared Report", name, "status") if prepared else "Completed"
	if status in RUNNING:
		frappe.msgprint(
			_("The report is still being prepared. You will receive an email on {0} with a download link once it is ready.").format(user_email)
		)
		return

	settle(request.name, status)
	if status == "Completed":
		frappe.msgprint(
			_("Your report is being generated in the background. You will receive an email on {0} with a download link once it is ready.").format(user_email)
		)
	else:
		frappe.msgprint(_("This report failed while it was being prepared. Please generate it again, then export."))


def request_key(report_name, filters, file_format, custom_columns):
	parts = (
		report_name,
		process_filters_for_prepared_report(filters),
		file_format or "",
		frappe.as_json(frappe.parse_json(custom_columns or "[]"), indent=None),
	)
	return hashlib.sha1("|".join(parts).encode()).hexdigest()


def repeat_click(user, key):
	return frappe.db.exists(
		"Report Export Request",
		[
			["user", "=", user],
			["request_key", "=", key],
			["status", "in", (WAITING, QUEUED)],
		],
	) or frappe.db.exists(
		"Report Export Request",
		[
			["user", "=", user],
			["request_key", "=", key],
			["status", "=", SENT],
			["creation", ">", add_to_date(now_datetime(), seconds=-REPEAT_CLICK_SECONDS)],
		],
	)


def claim(request):
	return move(request, QUEUED)


def move(request, status, error=None):
	frappe.db.sql(
		"""UPDATE `tabReport Export Request` SET status = %s, error = %s, modified = %s
		WHERE name = %s AND status = %s""",
		(status, error, now(), request, WAITING),
	)
	return frappe.db._cursor.rowcount == 1


def settle(request, prepared_status):
	if prepared_status in RUNNING:
		return
	if prepared_status != "Completed":
		fail_waiting(request, _("The report failed while it was being prepared."))
		return
	if claim(request):
		frappe.enqueue(
			"victoryfarmsdeveloper.setup.report_exports.build_export",
			queue="long",
			request=request,
			enqueue_after_commit=True,
		)


def build_export(request):
	doc = frappe.get_doc("Report Export Request", request)
	if doc.status != QUEUED:
		return
	frappe.set_user(doc.user)
	user_email = frappe.db.get_value("User", doc.user, "email")
	try:
		query_report.run_export_query_job(
			user_email,
			frappe._dict(json.loads(doc.form_params)),
			json.loads(doc.csv_params),
		)
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Report export failed", reference_doctype="Report Export Request", reference_name=doc.name)
		fail_request(doc, _("The export could not be built."))
		frappe.db.commit()
		return
	doc.db_set("status", SENT)


def fail_waiting(request, reason):
	if move(request, FAILED, reason):
		notify_failure(frappe.get_doc("Report Export Request", request), reason)


def fail_request(request, reason):
	request.db_set({"status": FAILED, "error": reason})
	notify_failure(request, reason)


def notify_failure(request, reason):
	recipient = frappe.db.get_value("User", request.user, "email")
	if recipient:
		frappe.sendmail(
			recipients=[recipient],
			subject=_("Your export of {0} could not be made").format(_(request.report_name)),
			message=_("{0} Please open {1}, generate it again and export.").format(reason, _(request.report_name)),
		)


def release_waiting_exports(doc, method=None):
	if doc.status in RUNNING or doc.report_name not in background_reports():
		return
	frappe.enqueue(
		"victoryfarmsdeveloper.setup.report_exports.release_exports_for",
		queue="short",
		prepared_report=doc.name,
		enqueue_after_commit=True,
	)


def release_exports_for(prepared_report):
	status = frappe.db.get_value("Prepared Report", prepared_report, "status")
	for name in frappe.get_all(
		"Report Export Request",
		filters={"prepared_report": prepared_report, "status": WAITING},
		pluck="name",
	):
		settle(name, status)
	frappe.db.commit()


def sweep_waiting_exports():
	for name, prepared_report in frappe.get_all(
		"Report Export Request",
		filters={"status": WAITING},
		fields=["name", "prepared_report"],
		as_list=True,
	):
		settle(name, frappe.db.get_value("Prepared Report", prepared_report, "status"))
		frappe.db.commit()
