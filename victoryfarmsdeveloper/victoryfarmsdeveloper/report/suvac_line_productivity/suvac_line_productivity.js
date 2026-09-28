// Copyright (c) 2026, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["SUVAC Line Productivity"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "stock_entry_type",
			label: __("Stock Entry Type"),
			fieldtype: "Select",
			options: ["", "Harvesting of Fish", "Fish Processing SUVAC"],
		},
		{
			fieldname: "processing_line",
			label: __("Processing Line"),
			fieldtype: "Int",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			default: "KPC-02-SUV-120MT - VFL",
		},
	],
	tree: true,
	name_field: "id",
	parent_field: "parent_id",
	initial_depth: 0,
};
