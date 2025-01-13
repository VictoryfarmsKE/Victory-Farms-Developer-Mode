frappe.ui.form.on("Appraisal", {
    refresh: function (frm) {
        cur_frm.set_query("appraisal_template", function () {
            return {
                filters: {
                    employee_template: 1,
                },
            };
        });
    },
    validate: function (frm) {
        if (frm.doc.docstatus === 0) {
            frm.doc.total_goal_score_percentage = (frm.doc.total_score / 5) * 100;
            cur_frm.refresh_field("total_goal_score_percentage");
        }
    },
});

frappe.ui.form.on("Appraisal Goal", {
    score_percentage: function (frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        let score = (row.score_percentage * 5) / 100;
        frappe.model.set_value(cdt, cdn, "score", score);
    },
    score: function (frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        let score_percentage = (row.score / 5) * 100;
        frappe.model.set_value(cdt, cdn, "score_percentage", score_percentage);
    },
    custom_did_the_employee: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.custom_did_the_employee) {
            frappe.db.get_value('Appraisal Template Goal', row.custom_did_the_employee, 'custom_did_the_employee', (r) => {
                if (r && r.custom_did_the_employee) {
                    frappe.model.set_value(cdt, cdn, 'custom_did_the_employee', r.custom_did_the_employee);
                }
            });
        }
    },
});
