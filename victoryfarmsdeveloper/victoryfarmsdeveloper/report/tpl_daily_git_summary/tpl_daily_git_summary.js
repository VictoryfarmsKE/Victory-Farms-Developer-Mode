// Copyright (c) 2026, Christine K and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["TPL Daily GIT Summary"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "vehicle",
			label: __("Vehicle"),
			fieldtype: "Link",
			options: "Warehouse",
			reqd: 0,
		},
		{
			fieldname: "driver",
			label: __("Driver"),
			fieldtype: "Link",
			options: "Driver",
			reqd: 0,
		},
		{
			fieldname: "source_warehouse",
			label: __("LC (Source Warehouse)"),
			fieldtype: "Link",
			options: "Warehouse",
			reqd: 0,
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
			reqd: 0,
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "MultiSelectList",
			width: "80",
			reqd: 1,
			default: ["Gutted Fish-Tilapia"],
			get_data: function(txt) {
				return frappe.db.get_link_options("Item Group", txt);
			}
		},
		{
			fieldname: "asp",
			label: __("ASP (Average Selling Price)"),
			fieldtype: "Float",
			default: 410,
			reqd: 1,
		},
	],
};
