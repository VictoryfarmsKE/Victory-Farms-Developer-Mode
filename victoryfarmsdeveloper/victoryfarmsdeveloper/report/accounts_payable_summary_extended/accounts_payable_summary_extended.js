// Copyright (c) 2026, Christine K and contributors
// For license information, please see license.txt

frappe.query_reports["Accounts Payable Summary Extended"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "report_date",
            label: __("Posting Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "ageing_based_on",
            label: __("Ageing Based On"),
            fieldtype: "Select",
            options: "Posting Date\nDue Date",
            default: "Due Date",
        },
        {
            fieldname: "calculate_ageing_with",
            label: __("Calculate Ageing With"),
            fieldtype: "Select",
            options: "Report Date\nToday Date",
            default: "Report Date",
        },
        {
            fieldname: "range",
            label: __("Ageing Range"),
            fieldtype: "Data",
            default: "30, 60, 90, 120",
        },
        {
            fieldname: "finance_book",
            label: __("Finance Book"),
            fieldtype: "Link",
            options: "Finance Book",
        },
        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_link_options("Cost Center", txt, {
                    company: frappe.query_report.get_filter_value("company"),
                });
            },
            options: "Cost Center",
        },
        {
            fieldname: "party_type",
            label: __("Party Type"),
            fieldtype: "Autocomplete",
            options: get_party_type_options(),
            on_change: function () {
                frappe.query_report.set_filter_value("party", "");
                frappe.query_report.toggle_filter_display(
                    "supplier_group",
                    frappe.query_report.get_filter_value("party_type") !== "Supplier"
                );
            },
        },
        {
            fieldname: "party",
            label: __("Party"),
            fieldtype: "MultiSelectList",
            options: "party_type",
            get_data: function (txt) {
                if (!frappe.query_report.filters) return;

                let party_type = frappe.query_report.get_filter_value("party_type");
                if (!party_type) return;

                return frappe.db.get_link_options(party_type, txt);
            },
        },
        {
            fieldname: "payment_terms_template",
            label: __("Payment Terms Template"),
            fieldtype: "Link",
            options: "Payment Terms Template",
        },
        {
            fieldname: "supplier_group",
            label: __("Supplier Group"),
            fieldtype: "Link",
            options: "Supplier Group",
        },
        {
            fieldname: "based_on_payment_terms",
            label: __("Based On Payment Terms"),
            fieldtype: "Check",
        },
        {
            fieldname: "for_revaluation_journals",
            label: __("Revaluation Journals"),
            fieldtype: "Check",
        },
        {
            fieldname: "show_gl_balance",
            label: __("Show GL Balance"),
            fieldtype: "Check",
        },
    ],

    onload: function (report) {
        report.page.add_inner_button(__("Accounts Payable"), function () {
            var filters = report.get_values();
            frappe.set_route("query-report", "Accounts Payable", { company: filters.company });
        });

        if (frappe.boot.sysdefaults.default_ageing_range) {
            report.set_filter_value("range", frappe.boot.sysdefaults.default_ageing_range);
        }
    },

    get_datatable_options(options) {
        return Object.assign(options, {
            headerGroups: [
                { html: '', colspan: 6 },  // Party Type, Party, Supplier Name, Credit Days, Credit Limit, Outstanding
                { html: '<strong>Aged Balance</strong>', colspan: 5 },  // 5 not_due columns
                { html: '<strong>Overdue Balance</strong>', colspan: 6 }  // 6 overdue columns
            ]
        });
    },

};

erpnext.utils.add_dimensions("Accounts Payable Summary Extended", 9);

function get_party_type_options() {
    let options = [];
    frappe.db
        .get_list("Party Type", { filters: { account_type: "Payable" }, fields: ["name"] })
        .then((res) => {
            res.forEach((party_type) => {
                options.push(party_type.name);
            });
        });
    return options;
}