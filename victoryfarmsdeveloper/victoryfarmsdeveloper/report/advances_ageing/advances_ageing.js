// Copyright (c) 2026, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["Advances Ageing"] = {
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
			fieldname: "report_date",
			label: __("Report Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "range",
			label: __("Ageing Range"),
			fieldtype: "Data",
			default: "30, 60, 90, 120",
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "MultiSelectList",
			options: "Supplier",
			get_data: function (txt) {
				return frappe.db.get_link_options("Supplier", txt);
			},
		},
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Link",
			options: "Supplier Group",
		},
	],

	onload: function (report) {
		if (frappe.boot.sysdefaults.default_ageing_range) {
			report.set_filter_value("range", frappe.boot.sysdefaults.default_ageing_range);
		}
	},

	get_datatable_options(options) {
		return Object.assign(options, {
			headerGroups: [
				{ html: "", colspan: 4 },
				{ html: "<strong>Aged Balance</strong>", colspan: 5 },
				{ html: "", colspan: 2 },
			],
		});
	},
};
