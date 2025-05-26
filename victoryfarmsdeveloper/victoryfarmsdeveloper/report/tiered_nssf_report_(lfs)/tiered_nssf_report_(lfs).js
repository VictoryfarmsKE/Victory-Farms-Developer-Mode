// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Tiered NSSF Report (LFS)"] = {
	"filters": [
    {
      "fieldname": "from_date",
      "label": "From Date",
      "fieldtype": "Date",
      "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      "reqd": 1
      },
    {
      "fieldname": "to_date",
      "label": "To Date",
      "fieldtype": "Date",
      "default": frappe.datetime.get_today(),
      "reqd": 1
    },
    {
      "fieldname": "employee",
      "label": "Employee",
      "fieldtype": "Link",
      "options": "Employee"
    },
    {
      "fieldname": "company",
      "label": "Company",
      "fieldtype": "Link",
	  "default": "Victory Farms Ltd",
      "options": "Company"
    },
	{
		"fieldname": "docstatus",
		"label": __("Document Status"),
		"fieldtype": "Select",
		"options": ["Draft", "Submitted", "Cancelled"],
		"default": "Submitted",
		"width": "100px",
	},
  ]
};
