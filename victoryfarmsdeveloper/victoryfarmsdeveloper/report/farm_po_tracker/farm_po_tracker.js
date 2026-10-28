const FARM_PO_PRIORITY_COLOURS = {
	P1: "#e5484d",
	P2: "#ea7a2f",
	P3: "#f2b705",
	P4: "#8cc63f",
	P5: "#2e9e57",
};

frappe.query_reports["Farm PO Tracker"] = {
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
			label: __("PO Date From"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -6),
			reqd: 1,
		},
		{
			fieldname: "tracker_group",
			label: __("Group"),
			fieldtype: "Select",
			options: [
				"",
				"Hatchery",
				"Maintenance",
				"Processing",
				"Lake Operations",
				"Farm Warehouse",
				"Security",
				"Quality Control",
				"Waste Management",
				"Boats",
			],
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "priority",
			label: __("Priority Level"),
			fieldtype: "Select",
			options: ["", "P1", "P2", "P3", "P4", "P5"],
		},
		{
			fieldname: "received_days",
			label: __("Keep Received POs For (Days)"),
			fieldtype: "Int",
			default: 30,
		},
		{
			fieldname: "farm_groups_only",
			label: __("Farm Groups Only"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "overdue_only",
			label: __("Past ETA Only"),
			fieldtype: "Check",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) {
			return value;
		}
		if (column.fieldname === "priority" && FARM_PO_PRIORITY_COLOURS[data.priority]) {
			return `<div style="background:${FARM_PO_PRIORITY_COLOURS[data.priority]};color:#111;font-weight:600;text-align:center;border-radius:3px">${value}</div>`;
		}
		if (column.fieldname === "eta" && data.is_overdue) {
			return `<span style="color:var(--red-600);font-weight:600">${value}</span>`;
		}
		if (column.fieldname === "tracker_group") {
			return `<span style="font-weight:600">${value}</span>`;
		}
		return value;
	},
};
