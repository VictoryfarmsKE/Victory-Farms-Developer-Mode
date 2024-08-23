// Copyright (c) 2024, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Sales (Gutted Fish)"] = {
	filters: [
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
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			reqd: 0,
		},
		{
			fieldname: "show_with_zero_values",
			label: __("Show with zero values"),
			fieldtype: "Check",
			default: 0,
		},
	  ],
};
