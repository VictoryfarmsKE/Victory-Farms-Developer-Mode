# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate

from hrms.hr.doctype.leave_allocation.leave_allocation import get_previous_allocation
from hrms.hr.doctype.leave_application.leave_application import (
	get_leave_balance_on,
	get_leaves_for_period,
)

Filters = frappe._dict


def execute(filters: Filters | None = None) -> tuple:
	if filters.to_date <= filters.from_date:
		frappe.throw(_('"From Date" can not be greater than or equal to "To Date"'))

	columns = get_columns()
	data = get_data(filters)
	return columns, data, None

def get_columns() -> list[dict]:
    return [
        {
            "label": _("Payroll Number"),
            "fieldtype": "Data",
            "fieldname": "employee_number",
            "width": 150,
        },
        {
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "fieldname": "employee_name",
            "width": 200,
        },
        {
            "label": _("Department"),
            "fieldtype": "Link",
            "fieldname": "department",
            "width": 220,
            "options": "Department",
        },
        {
            "label": _("Daily CTC"),
            "fieldtype": "Data",
            "fieldname": "ctc",
            "width": 180,
        },
        {
            "label": _("Salary Currency"),
            "fieldtype": "Link",
            "fieldname": "salary_currency",
            "width": 150,
            "options": "Currency",
        },
        {
            "label": _("Leave Type"),
            "fieldtype": "Link",
            "fieldname": "leave_type",
            "width": 200,
            "options": "Leave Type",
        },
        {
            "label": _("Closing Balance"),
            "fieldtype": "float",
            "fieldname": "closing_balance",
            "width": 150,
        },
        {
            "label": _("Leave Liability"),
            "fieldtype": "Data",
            "fieldname": "leave_liability",
            "width": 180,
        },
    ]

def get_data(filters: Filters) -> list:
    leave_types = ["Annual Leave C&D Level"]
    active_employees = get_employees(filters)

    precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
    row = None

    data = []

    for leave_type in leave_types:
        for employee in active_employees:
            row = frappe._dict({"leave_type": leave_type})

            row.employee = employee.name
            row.employee_name = employee.employee_name
            row.employee_number = employee.employee_number
            row.department = employee.department
            daily_ctc = round(employee.ctc / 31, 2)
            row.ctc = "{:.2f}".format(daily_ctc)
            row.salary_currency = employee.salary_currency

            leaves_taken = (
                get_leaves_for_period(employee.name, leave_type, filters.from_date, filters.to_date) * -1
            )

            new_allocation, expired_leaves, carry_forwarded_leaves = get_allocated_and_expired_leaves(
                filters.from_date, filters.to_date, employee.name, leave_type
            )

            if new_allocation:
                opening = get_opening_balance(employee.name, leave_type, filters, carry_forwarded_leaves)

                row.leaves_allocated = flt(new_allocation, precision)
                row.leaves_expired = flt(expired_leaves, precision)
                row.opening_balance = flt(opening, precision)
                row.leaves_taken = flt(leaves_taken, precision)

                closing = new_allocation + opening - (row.leaves_expired + leaves_taken)
                row.closing_balance = flt(closing, precision)
                closing_balance = row.closing_balance
                leave_liability = round(closing_balance * daily_ctc, 2)
                row.leave_liability = "{:.2f}".format(leave_liability)
                row.indent = 1
                data.append(row)

    return data

def get_employees(filters: Filters) -> list[dict]:
    Employee = frappe.qb.DocType("Employee")
    query = frappe.qb.from_(Employee).select(
        Employee.name,
        Employee.employee_name,
        Employee.employee_number,
        Employee.department,
        Employee.ctc,
        Employee.salary_currency,
    )

    for field in ["company", "department"]:
        if filters.get(field):
            query = query.where(getattr(Employee, field) == filters.get(field))

    if filters.get("employee"):
        query = query.where(Employee.name == filters.get("employee"))
        
    query = query.where(Employee.status == "Active")

    return query.run(as_dict=True)

def get_leave_types() -> list[str]:
	LeaveType = frappe.qb.DocType("Leave Type")
	return (frappe.qb.from_(LeaveType).select(LeaveType.name).orderby(LeaveType.name)).run(pluck="name")


def get_opening_balance(
	employee: str, leave_type: str, filters: Filters, carry_forwarded_leaves: float
) -> float:
	# allocation boundary condition
	# opening balance is the closing leave balance 1 day before the filter start date
	opening_balance_date = add_days(filters.from_date, -1)
	allocation = get_previous_allocation(filters.from_date, leave_type, employee)

	if (
		allocation
		and allocation.get("to_date")
		and opening_balance_date
		and getdate(allocation.get("to_date")) == getdate(opening_balance_date)
	):
		# if opening balance date is same as the previous allocation's expiry
		# then opening balance should only consider carry forwarded leaves
		opening_balance = carry_forwarded_leaves
	else:
		# else directly get leave balance on the previous day
		opening_balance = get_leave_balance_on(employee, leave_type, opening_balance_date)

	return opening_balance


def get_allocated_and_expired_leaves(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> tuple[float, float, float]:
	new_allocation = 0
	expired_leaves = 0
	carry_forwarded_leaves = 0

	records = get_leave_ledger_entries(from_date, to_date, employee, leave_type)

	for record in records:
		# new allocation records with `is_expired=1` are created when leave expires
		# these new records should not be considered, else it leads to negative leave balance
		if record.is_expired:
			continue

		if record.to_date < getdate(to_date):
			# leave allocations ending before to_date, reduce leaves taken within that period
			# since they are already used, they won't expire
			expired_leaves += record.leaves
			leaves_for_period = get_leaves_for_period(employee, leave_type, record.from_date, record.to_date)
			expired_leaves -= min(abs(leaves_for_period), record.leaves)

		if record.from_date >= getdate(from_date):
			if record.is_carry_forward:
				carry_forwarded_leaves += record.leaves
			else:
				new_allocation += record.leaves

	return new_allocation, expired_leaves, carry_forwarded_leaves


def get_leave_ledger_entries(from_date: str, to_date: str, employee: str, leave_type: str) -> list[dict]:
	ledger = frappe.qb.DocType("Leave Ledger Entry")
	return (
		frappe.qb.from_(ledger)
		.select(
			ledger.employee,
			ledger.leave_type,
			ledger.from_date,
			ledger.to_date,
			ledger.leaves,
			ledger.transaction_name,
			ledger.transaction_type,
			ledger.is_carry_forward,
			ledger.is_expired,
		)
		.where(
			(ledger.docstatus == 1)
			& (ledger.transaction_type == "Leave Allocation")
			& (ledger.employee == employee)
			& (ledger.leave_type == leave_type)
			& (
				(ledger.from_date[from_date:to_date])
				| (ledger.to_date[from_date:to_date])
				| ((ledger.from_date < from_date) & (ledger.to_date > to_date))
			)
		)
	).run(as_dict=True)

