// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["Bank Template (Bonus Pay)"] = {
	"filters": [
		{
            "fieldname": "posting_date",
            "label": __("Posting Date"),
            "fieldtype": "Date",
            "reqd": 1  
        },
        // {
        //     "fieldname": "start_date",
        //     "label": __("Start Date"),
        //     "fieldtype": "Date",
        //     "default": frappe.datetime.add_months(frappe.datetime.nowdate(), -1),
        //     "reqd": 0  
        // },
        // {
        //     "fieldname": "end_date",
        //     "label": __("End Date"),
        //     "fieldtype": "Date",
        //     "default": frappe.datetime.nowdate(),
        //     "reqd": 0  
        // },
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
            "reqd": 1  
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

