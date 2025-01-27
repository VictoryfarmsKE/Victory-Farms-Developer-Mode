// Copyright (c) 2024, Christine K and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Appraisal Bonus Payout"] = {
	"filters": [
        {
            "fieldname": "start_date",
            "label": __("Start Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.nowdate(), -1),
            "reqd": 0  
        },
        {
            "fieldname": "end_date",
            "label": __("End Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.nowdate(),
            "reqd": 0  
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
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "reqd": 0, 
        },
        {
            "fieldname": "payout_frequency",
            "label": __("Payout Frequency"),
            "fieldtype": "Select",
            "options": ["", "Monthly", "Quarterly", "Annually"],
            "reqd": 0  
        },
        {
            "fieldname": "posting_date",
            "label": __("Posting Date"),
            "fieldtype": "Date",
            "reqd": 0  
        },
        // {
        //     "fieldname": "employee",
        //     "label": __("Employee"),
        //     "fieldtype": "Link",
        //     "options": "Employee",
        //     "reqd": 0  
        // }
    ]
};

