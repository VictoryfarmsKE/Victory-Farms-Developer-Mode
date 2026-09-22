// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Pending Purchase Order Report"] = {
	"filters": [
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department"
		}
	]
};
