// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Leave Liability Report"] = {
	"filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.year_start(),
            "reqd": 0  
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.year_end(),
            "reqd": 0  
        },
		{
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "reqd": 0, 
        },
        {
            "fieldname": "leave_type",
            "label": __("Leave Type"),
            "fieldtype": "Link",
			"options": "Leave Type",
			"default": "Annual Leave",
            "reqd": 0,
			"read_only": 1 
        }
    ]
};

