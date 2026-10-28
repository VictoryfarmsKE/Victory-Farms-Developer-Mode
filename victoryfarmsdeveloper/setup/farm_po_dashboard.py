import frappe
from frappe import _
from frappe.utils import add_months, today

from victoryfarmsdeveloper.victoryfarmsdeveloper.report.farm_po_tracker.farm_po_tracker import (
	PRIORITIES,
	TRACKER_GROUPS,
	get_rows,
)

REPORT_ROUTE = ["query-report", "Farm PO Tracker"]
TT_WINDOW_DAYS = 90
NOT_SET = "Not Set"


def dashboard_filters(filters=None, received_days=TT_WINDOW_DAYS):
	filters = frappe._dict(frappe.parse_json(filters) or {})
	return frappe._dict(
		company=filters.company or frappe.defaults.get_user_default("Company"),
		from_date=filters.from_date or add_months(today(), -6),
		received_days=filters.received_days or received_days,
		farm_groups_only=1,
	)


def dashboard_rows(filters=None):
	filters = dashboard_filters(filters)
	return get_rows(filters), filters


def open_rows(filters=None):
	rows, filters = dashboard_rows(filters)
	return [row for row in rows if not row.received_on], filters


def card(value, filters, fieldtype="Int", **route_filters):
	return {
		"value": value,
		"fieldtype": fieldtype,
		"route": REPORT_ROUTE,
		"route_options": {
			"company": filters.company,
			"from_date": filters.from_date,
			"received_days": filters.received_days,
			**route_filters,
		},
	}


def average(values):
	return round(sum(values) / len(values), 1) if values else None


def ordered_groups(rows):
	present = {row.tracker_group for row in rows}
	return [group for group in TRACKER_GROUPS if group in present] + sorted(present - set(TRACKER_GROUPS))


@frappe.whitelist()
def open_pos_card(filters=None):
	rows, filters = open_rows(filters)
	return card(len(rows), filters)


@frappe.whitelist()
def past_eta_card(filters=None):
	rows, filters = open_rows(filters)
	return card(sum(row.is_overdue for row in rows), filters, overdue_only=1)


@frappe.whitelist()
def no_priority_card(filters=None):
	rows, filters = open_rows(filters)
	return card(sum(1 for row in rows if not row.priority), filters)


@frappe.whitelist()
def average_tt_card(filters=None):
	rows, filters = dashboard_rows(filters)
	value = average([row.actual_tt for row in rows if row.actual_tt is not None])
	return {**card(value, filters, fieldtype="Float"), "precision": 1}


@frappe.whitelist()
def tt_by_priority(chart_name=None, chart=None, no_cache=None, filters=None, **kwargs):
	rows, _filters = dashboard_rows(filters)
	averages = {p: average([r.actual_tt for r in rows if r.priority == p and r.actual_tt is not None]) for p in PRIORITIES}
	averages = {p: value for p, value in averages.items() if value is not None}
	return {
		"labels": list(averages),
		"datasets": [{"name": _("Average Actual T/T (Days)"), "values": list(averages.values())}],
	}


@frappe.whitelist()
def tt_by_group(chart_name=None, chart=None, no_cache=None, filters=None, **kwargs):
	rows, _filters = dashboard_rows(filters)
	received = [row for row in rows if row.actual_tt is not None]
	groups = ordered_groups(received)
	return {
		"labels": groups,
		"datasets": [
			{
				"name": _("Average Actual T/T (Days)"),
				"values": [average([r.actual_tt for r in received if r.tracker_group == g]) for g in groups],
			}
		],
	}


@frappe.whitelist()
def open_by_group(chart_name=None, chart=None, no_cache=None, filters=None, **kwargs):
	rows, _filters = open_rows(filters)
	groups = ordered_groups(rows)
	return {
		"labels": groups,
		"datasets": [
			{"name": _("Open"), "values": [sum(1 for r in rows if r.tracker_group == g) for g in groups]},
			{"name": _("Past ETA"), "values": [sum(r.is_overdue for r in rows if r.tracker_group == g) for g in groups]},
		],
	}


@frappe.whitelist()
def open_by_status(chart_name=None, chart=None, no_cache=None, filters=None, **kwargs):
	rows, _filters = open_rows(filters)
	counts = {}
	for row in rows:
		status = row.delivery_status or _(NOT_SET)
		counts[status] = counts.get(status, 0) + 1
	return {
		"labels": list(counts),
		"datasets": [{"name": _("Open POs"), "values": list(counts.values())}],
	}
