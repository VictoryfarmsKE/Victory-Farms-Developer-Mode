// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["USD Bank Template (Base Pay)"] = {
	"filters": [
		{
		"fieldname":"from_date",
		"label": __("From Date"),
		"fieldtype": "Date",
		"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		"reqd": 1,
		"width": "80"
	},
	{
		"fieldname":"to_date",
		"label": __("To Date"),
		"fieldtype": "Date",
		"default": frappe.datetime.get_today(),
		"reqd": 1,
		"width": "80"
	}
	]
};
