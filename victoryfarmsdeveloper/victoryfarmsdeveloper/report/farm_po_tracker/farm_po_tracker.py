import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, date_diff, flt, getdate, today

TRACKER_GROUPS = (
	"Hatchery",
	"Maintenance",
	"Processing",
	"Lake Operations",
	"Farm Warehouse",
	"Security",
	"Quality Control",
	"Waste Management",
	"Boats",
)
PRIORITIES = ("P1", "P2", "P3", "P4", "P5")
PRIORITY_COLOURS = {"P1": "#e5484d", "P2": "#ea7a2f", "P3": "#f2b705", "P4": "#8cc63f", "P5": "#2e9e57"}
EXCLUDED_WORKFLOW_STATES = ("Cancelled", "Frozen")
RECEIVED = "Received at Farm"
PARTIALLY_DELIVERED = "Partially Delivered"
GROUP_EXPRESSION = "coalesce(nullif(po.custom_po_tracker_group, ''), dept.custom_po_tracker_group)"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = get_rows(filters)
	return get_columns(), rows, None, get_chart(rows), get_summary(rows)


def get_columns():
	return [
		{"label": _("Group"), "fieldname": "tracker_group", "fieldtype": "Data", "width": 130},
		{"label": _("P.O Number"), "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 140},
		{"label": _("PO Status"), "fieldname": "po_status", "fieldtype": "Data", "width": 150},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 280},
		{"label": _("Date of P.O Creation"), "fieldname": "po_date", "fieldtype": "Date", "width": 110},
		{"label": _("Priority Level"), "fieldname": "priority", "fieldtype": "Data", "width": 80},
		{"label": _("ETA - Farm"), "fieldname": "eta", "fieldtype": "Date", "width": 105},
		{"label": _("Planned Lead Time (Days)"), "fieldname": "planned_lead_time", "fieldtype": "Int", "width": 110},
		{"label": _("Received On"), "fieldname": "received_on", "fieldtype": "Date", "width": 105},
		{"label": _("Actual T/T (Days)"), "fieldname": "actual_tt", "fieldtype": "Int", "width": 100},
		{"label": _("Days Open"), "fieldname": "days_open", "fieldtype": "Int", "width": 90},
		{"label": _("Status"), "fieldname": "delivery_status", "fieldtype": "Data", "width": 150},
		{"label": _("Comments"), "fieldname": "comment", "fieldtype": "Data", "width": 280},
		{"label": _("Comment Updated On"), "fieldname": "comment_updated_on", "fieldtype": "Datetime", "width": 150},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 180},
		{"label": _("Supplier"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
	]


def get_rows(filters):
	orders = get_orders(filters)
	if not orders:
		return []

	names = [order.name for order in orders]
	received_on = get_received_dates(names)
	first_items = get_first_items(names)
	cutoff = add_days(today(), -cint(filters.received_days or 30))

	rows = []
	for order in orders:
		row = build_row(order, received_on.get(order.name), first_items.get(order.name))
		if row.received_on and getdate(row.received_on) < getdate(cutoff):
			continue
		if filters.overdue_only and not row.is_overdue:
			continue
		rows.append(row)

	rows.sort(key=sort_key)
	return rows


def get_orders(filters):
	conditions = []
	values = {
		"company": filters.company,
		"from_date": filters.from_date or add_months(today(), -6),
		"excluded_states": EXCLUDED_WORKFLOW_STATES,
	}

	if filters.tracker_group:
		conditions.append(f"{GROUP_EXPRESSION} = %(tracker_group)s")
		values["tracker_group"] = filters.tracker_group
	elif cint(filters.farm_groups_only):
		conditions.append(f"ifnull({GROUP_EXPRESSION}, '') != ''")

	if filters.department:
		conditions.append("po.custom_department = %(department)s")
		values["department"] = filters.department

	if filters.priority:
		conditions.append("po.custom_priority_level = %(priority)s")
		values["priority"] = filters.priority

	extra = "".join(f" and {condition}" for condition in conditions)
	description = "po.custom_po_description" if frappe.get_meta("Purchase Order").has_field("custom_po_description") else "null"

	return frappe.db.sql(
		f"""
		select
			po.name, po.docstatus, po.workflow_state, po.status, po.transaction_date,
			po.custom_department, {GROUP_EXPRESSION} as custom_po_tracker_group, po.supplier_name,
			{description} as custom_po_description, po.custom_priority_level, po.custom_eta,
			po.custom_shipment_status, po.custom_procurement_comment,
			po.custom_comment_updated_on, po.per_received
		from `tabPurchase Order` po
		left join `tabDepartment` dept on dept.name = po.custom_department
		where po.company = %(company)s
			and po.docstatus < 2
			and po.status not in ('Closed', 'Cancelled')
			and ifnull(po.workflow_state, '') not in %(excluded_states)s
			and po.transaction_date >= %(from_date)s
			{extra}
		""",
		values,
		as_dict=True,
	)


def get_received_dates(names):
	return dict(
		frappe.db.sql(
			"""
			select pri.purchase_order, max(pr.posting_date)
			from `tabPurchase Receipt Item` pri
			inner join `tabPurchase Receipt` pr on pr.name = pri.parent
			where pr.docstatus = 1 and pri.purchase_order in %(names)s
			group by pri.purchase_order
			""",
			{"names": names},
		)
	)


def get_first_items(names):
	first_items = {}
	for parent, item_name, item_count in frappe.db.sql(
		"""
		select parent, substring_index(group_concat(item_name order by idx separator '\n'), '\n', 1), count(*)
		from `tabPurchase Order Item`
		where parent in %(names)s
		group by parent
		""",
		{"names": names},
	):
		first_items[parent] = item_name if item_count == 1 else _("{0} + {1} more").format(item_name, item_count - 1)
	return first_items


def build_row(order, last_receipt, first_item):
	fully_received = flt(order.per_received) >= 100
	received_on = last_receipt if fully_received else None
	eta = order.custom_eta

	if fully_received:
		delivery_status = RECEIVED
	elif flt(order.per_received) > 0:
		delivery_status = PARTIALLY_DELIVERED
	else:
		delivery_status = order.custom_shipment_status

	return frappe._dict(
		tracker_group=order.custom_po_tracker_group or order.custom_department,
		purchase_order=order.name,
		po_status=order.workflow_state or (_("Draft") if order.docstatus == 0 else order.status),
		item_name=order.custom_po_description or first_item,
		po_date=order.transaction_date,
		priority=order.custom_priority_level,
		eta=eta,
		planned_lead_time=date_diff(eta, order.transaction_date) if eta else None,
		received_on=received_on,
		actual_tt=date_diff(received_on, order.transaction_date) if received_on else None,
		days_open=None if received_on else date_diff(today(), order.transaction_date),
		delivery_status=delivery_status,
		comment=order.custom_procurement_comment,
		comment_updated_on=order.custom_comment_updated_on,
		department=order.custom_department,
		supplier_name=order.supplier_name,
		is_overdue=1 if eta and not fully_received and getdate(eta) < getdate(today()) else 0,
	)


def sort_key(row):
	group_rank = TRACKER_GROUPS.index(row.tracker_group) if row.tracker_group in TRACKER_GROUPS else len(TRACKER_GROUPS)
	priority_rank = PRIORITIES.index(row.priority) if row.priority in PRIORITIES else len(PRIORITIES)
	return (group_rank, row.tracker_group or "", 1 if row.received_on else 0, priority_rank, row.po_date)


def average_actual_tt(rows, priority):
	values = [row.actual_tt for row in rows if row.priority == priority and row.actual_tt is not None]
	return round(sum(values) / len(values), 1) if values else None


def get_chart(rows):
	averages = {p: average_actual_tt(rows, p) for p in PRIORITIES}
	averages = {p: value for p, value in averages.items() if value is not None}
	if not averages:
		return None
	return {
		"data": {
			"labels": list(averages),
			"datasets": [{"name": _("Average Actual T/T (Days)"), "values": list(averages.values())}],
		},
		"type": "bar",
		"colors": ["#2e9e57"],
	}


def get_summary(rows):
	open_rows = [row for row in rows if not row.received_on]
	received = [row.actual_tt for row in rows if row.actual_tt is not None]
	average_tt = f"{sum(received) / len(received):.1f}" if received else "-"
	return [
		{"label": _("Open POs"), "value": len(open_rows), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Past ETA"), "value": sum(row.is_overdue for row in rows), "datatype": "Int", "indicator": "Red"},
		{"label": _("No Priority Set"), "value": sum(1 for row in open_rows if not row.priority), "datatype": "Int", "indicator": "Orange"},
		{"label": _("No ETA Set"), "value": sum(1 for row in open_rows if not row.eta), "datatype": "Int", "indicator": "Orange"},
		{"label": _("Average Actual T/T (Days)"), "value": average_tt, "datatype": "Data", "indicator": "Green"},
	]
