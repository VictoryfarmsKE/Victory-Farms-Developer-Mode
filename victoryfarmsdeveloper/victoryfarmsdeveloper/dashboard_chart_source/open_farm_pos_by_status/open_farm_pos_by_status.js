frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Open Farm POs by Status"] = {
	method: "victoryfarmsdeveloper.setup.farm_po_dashboard.open_by_status",
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
