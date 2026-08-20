# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import getdate, today


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data, filters)

	return columns, data, None, chart


def validate_filters(filters) -> None:
	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.from_date) > getdate(filters.to_date):
			frappe.throw(_("From Date cannot be after To Date"))


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Tardiness Record"),
			"fieldname": "tardiness_record",
			"fieldtype": "Link",
			"options": "Tardiness Record",
			"width": 200,
		},
		{
			"label": _("Employee"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200,
		},
		# {
		# 	"label": _("Date"),
		# 	"fieldname": "date",
		# 	"fieldtype": "Date",
		# 	"width": 95,
		# },
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Reason"),
			"fieldname": "description",
			"fieldtype": "Small Text",
			"width": 200,
		},
		# {
		# 	"label": _("Attendance"),
		# 	"fieldname": "attendance",
		# 	"fieldtype": "Link",
		# 	"options": "Attendance",
		# 	"width": 150,
		# },
		{
			"label": _("Attendance Date"),
			"fieldname": "attendance_date",
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"label": _("Shift Start Time"),
			"fieldname": "shift_start_time",
			"fieldtype": "Time",
			"width": 150,
		},
		{
			"label": _("Actual Checkin Time"),
			"fieldname": "actual_checkin_time",
			"fieldtype": "Datetime",
			"width": 200,
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 200,
		},
		
		{
			"label": _("Approver Name"),
			"fieldname": "approver_name",
			"fieldtype": "Data",
			"width": 150,
		},
	]


def get_data(filters) -> list[dict]:
	conditions = ["tr.docstatus != 2"]
	values = {}

	if filters.get("from_date"):
		conditions.append("tr.attendance_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("tr.attendance_date <= %(to_date)s")
		values["to_date"] = filters.to_date
	if filters.get("employee"):
		conditions.append("tr.employee = %(employee)s")
		values["employee"] = filters.employee
	if filters.get("department"):
		conditions.append("tr.department = %(department)s")
		values["department"] = filters.department
	if filters.get("status"):
		conditions.append("tr.status = %(status)s")
		values["status"] = filters.status
	if filters.get("approver"):
		conditions.append("tr.approver = %(approver)s")
		values["approver"] = filters.approver

	rows = frappe.db.sql(
		f"""
		SELECT
			tr.name AS tardiness_record,
			tr.employee_name,
			tr.attendance_date AS date,
			tr.status,
			tr.description,
			tr.attendance,
			tr.attendance_date,
			tr.actual_checkin_time,
			tr.department,
			st.start_time AS shift_start_time,
			tr.approver_name
		FROM `tabTardiness Record` tr
		LEFT JOIN `tabAttendance` att ON att.name = tr.attendance
		LEFT JOIN `tabShift Type` st ON st.name = COALESCE(tr.shift_type, att.shift)
		WHERE {' AND '.join(conditions)}
		ORDER BY tr.attendance_date DESC, tr.actual_checkin_time DESC, tr.employee_name ASC
		""",
		values,
		as_dict=True,
	)

	return rows


def get_chart(data: list[dict], filters) -> dict:
	approved_by_date = {}
	rejected_by_date = {}

	for row in data:
		attendance_date = row.get("attendance_date")
		status = row.get("status")
		if not attendance_date or status not in {"Approved", "Rejected"}:
			continue

		label = str(attendance_date)
		if status == "Approved":
			approved_by_date[label] = approved_by_date.get(label, 0) + 1
		else:
			rejected_by_date[label] = rejected_by_date.get(label, 0) + 1

	labels = get_chart_labels(filters, approved_by_date, rejected_by_date)

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Approved"),
					"values": [approved_by_date.get(label, 0) for label in labels],
				},
				{
					"name": _("Rejected"),
					"values": [rejected_by_date.get(label, 0) for label in labels],
				},
			],
		},
		"type": "line",
		"height": 300,
		"colors": ["#2E7D32", "#C62828"],
	}


def get_chart_labels(filters, approved_by_date: dict, rejected_by_date: dict) -> list[str]:
	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else None
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else None

	if from_date and to_date:
		labels = []
		current_date = from_date
		while current_date <= to_date:
			labels.append(str(current_date))
			current_date += timedelta(days=1)
		return labels

	labels = sorted(set(approved_by_date) | set(rejected_by_date))
	if not labels:
		return [str(today())]

	return labels
