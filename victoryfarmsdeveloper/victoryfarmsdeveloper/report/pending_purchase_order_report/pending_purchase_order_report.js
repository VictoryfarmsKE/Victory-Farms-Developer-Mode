// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Pending Purchase Order Report"] = {
    filters: [
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "cost_center",
            label: __("Cost Centre"),
            fieldtype: "Link",
            options: "Cost Center"
        },
        {
            fieldname: "requester",
            label: __("Requester"),
            fieldtype: "Link",
            options: "User"
        },
        {
            fieldname: "created_by",
            label: __("Created By"),
            fieldtype: "Link",
            options: "User"
        }
    ]
};
