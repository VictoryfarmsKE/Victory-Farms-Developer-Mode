// Copyright (c) 2026, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["Tardiness Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nOpen\nApproved\nRejected\nCancelled",
		},
		{
			fieldname: "approver",
			label: __("Approver"),
			fieldtype: "Link",
			options: "User",
		},
	],
};
