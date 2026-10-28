from itertools import groupby
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_months, get_url, get_url_to_form, today
from frappe.utils.xlsxutils import make_xlsx

from victoryfarmsdeveloper.victoryfarmsdeveloper.report.farm_po_tracker.farm_po_tracker import (
	PRIORITY_COLOURS,
	get_columns,
	get_rows,
	get_summary,
)

EMAIL_GROUP = "Farm PO Tracker Daily"
TEMPLATE = "victoryfarmsdeveloper/templates/emails/farm_po_tracker.html"
SUMMARY_COLOURS = {"Blue": "#1f6fd1", "Red": "#c62828", "Orange": "#d9730d", "Green": "#1f7a4d"}
EMAIL_HEADINGS = ("P.O Number", "Item Name", "PO Date", "Priority", "ETA - Farm", "Status", "Days", "Comments")


def get_recipients():
	if not frappe.db.exists("Email Group", EMAIL_GROUP):
		return []
	return frappe.get_all(
		"Email Group Member", filters={"email_group": EMAIL_GROUP, "unsubscribed": 0}, pluck="email"
	)


def tracker_filters(company):
	return frappe._dict(
		company=company,
		from_date=add_months(today(), -6),
		received_days=30,
		farm_groups_only=1,
	)


def send_daily_tracker():
	recipients = get_recipients()
	if not recipients:
		return

	company = frappe.defaults.get_global_default("company")
	rows = get_rows(tracker_filters(company))
	if not rows:
		return

	frappe.sendmail(
		recipients=recipients,
		subject=_("Farm PO Tracker - {0}").format(frappe.utils.formatdate(today(), "d MMM yyyy")),
		message=render_email(rows, company),
		attachments=[{"fname": f"Farm PO Tracker {today()}.xlsx", "fcontent": build_xlsx(rows)}],
		reference_doctype="Email Group",
		reference_name=EMAIL_GROUP,
		add_unsubscribe_link=0,
	)


def render_email(rows, company):
	for row in rows:
		row.url = get_url_to_form("Purchase Order", row.purchase_order)
		row.priority_colour = PRIORITY_COLOURS.get(row.priority)

	summary = [
		frappe._dict(label=item["label"], value=item["value"], colour=SUMMARY_COLOURS.get(item["indicator"]))
		for item in get_summary(rows)
	]
	groups = [frappe._dict(name=name, rows=list(group)) for name, group in groupby(rows, key=lambda row: row.tracker_group)]

	return frappe.render_template(
		TEMPLATE,
		{
			"report_date": today(),
			"summary": summary,
			"headings": [_(heading) for heading in EMAIL_HEADINGS],
			"groups": groups,
			"report_url": get_url(f"/app/query-report/{quote('Farm PO Tracker')}?company={quote(company or '')}"),
		},
	)


def build_xlsx(rows):
	columns = get_columns()
	data = [[column["label"] for column in columns]]
	data.extend([row.get(column["fieldname"]) for column in columns] for row in rows)
	return make_xlsx(data, "Farm PO Tracker", column_widths=[column["width"] // 7 for column in columns]).getvalue()
