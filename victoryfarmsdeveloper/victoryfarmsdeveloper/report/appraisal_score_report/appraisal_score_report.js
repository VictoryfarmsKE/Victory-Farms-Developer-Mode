// Copyright (c) 2024, Christine K and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Appraisal Score Report"] = {
    filters: [
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            width: 150
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            width: 150
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            width: 150,
			"default": frappe.defaults.get_default("company")
        },
		{
            fieldname: "appraisal_cycle",
            label: __("Appraisal Cycle"),
            fieldtype: "Link",
            options: "Appraisal Cycle",
            width: 150
        },
		{
			fieldname: "docstatus",
			label: __("Document Status"),
			fieldtype: "Select",
			options: ["Draft", "Submitted", "Cancelled"],
			default: "Submitted",
			width: "100px",
		}
    ],

    get_chart_data: function(columns, result) {
        let employee_filter = frappe.query_report.get_filter_value("employee");
        if (employee_filter) {
            return get_employee_score_chart(result);
        }
        return null;
    }
};

function get_employee_score_chart(result) {
    if (result && result.length) {
        let employee_row = result[0]; 
        return {
            data: {
                labels: ["Department Score", "Individual Score", "Company Score"],
                datasets: [
                    {
                        name: __("Scores"),
                        values: [
                            employee_row.department_score || 0, 
                            employee_row.individual_score || 0, 
                            employee_row.company_score || 0
                        ]
                    }
                ]
            },
            type: "bar", 
            colors: [ "#10812E","#61CE70"]
        };
    }
    return null;
}
