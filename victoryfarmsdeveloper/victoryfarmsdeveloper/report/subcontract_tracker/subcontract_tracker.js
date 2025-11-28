// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["SubContract Tracker"] = {
	"filters": [
		{
			"fieldname":"purchase_order",
			"label": __("Purchase Order"),
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": "80"
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": "80"
		}

	]
};
