frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Farm PO Average Turnaround by Priority"] = {
	method: "victoryfarmsdeveloper.setup.farm_po_dashboard.tt_by_priority",
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
