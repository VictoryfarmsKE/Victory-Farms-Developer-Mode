// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["Casual Cost (KES per Kg)"] = {
	filters: [
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [
				"January",
				"February",
				"March",
				"April",
				"May",
				"June",
				"July",
				"August",
				"September",
				"October",
				"November",
				"December",
			],
			reqd: 1,
		},
		{
			fieldname: "year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
		},
	],
};
