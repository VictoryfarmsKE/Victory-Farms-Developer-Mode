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
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("User", txt);
                }
        },
        {
            fieldname: "page_length",
            label: __("Show"),
            fieldtype: "Select",
            options: [
                "50","100","250","500"
            ],
            default: "100"
        }
    ]
};
