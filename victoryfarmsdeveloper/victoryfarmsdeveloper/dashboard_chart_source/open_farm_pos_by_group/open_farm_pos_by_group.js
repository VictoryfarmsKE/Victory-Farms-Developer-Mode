frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Open Farm POs by Group"] = {
	method: "victoryfarmsdeveloper.setup.farm_po_dashboard.open_by_group",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
	],
};
