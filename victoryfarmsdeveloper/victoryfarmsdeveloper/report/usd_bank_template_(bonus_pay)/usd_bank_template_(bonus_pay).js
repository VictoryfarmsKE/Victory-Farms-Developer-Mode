// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["USD Bank Template (Bonus Pay)"] = {
	"filters": [
			{
            "fieldname": "posting_date",
            "label": __("Posting Date"),
            "fieldtype": "Date",
            "reqd": 1 
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 0,  
            "default": frappe.defaults.get_default("company"),
        },
        {
            "fieldname": "payout_frequency",
            "label": __("Payout Frequency"),
            "fieldtype": "Select",
            "options": ["", "Monthly", "Quarterly", "Annually"],
            "reqd": 1,
			"default": "Annually",
        },
		{
			fieldname: "docstatus",	
			label: __("Document Status"),
			fieldtype: "Select",
			options: [
				{ "value": "", "label": __("All") },
				{ "value": "0", "label": __("Draft") },
				{ "value": "1", "label": __("Submitted") },
				{ "value": "2", "label": __("Cancelled") },
			],
			default: "1",
		}
	]
};
