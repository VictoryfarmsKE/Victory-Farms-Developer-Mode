// ============================================================
// EMPLOYEE ONBOARDING FORM - CLIENT SCRIPT
// Paste this entire block into:
// ERPNext > Awesome Bar > Client Script > + Add Client Script
// Doctype: Employee | Script Type: Form | Enabled: checked
// ============================================================

frappe.ui.form.on('Employee', {

    // --- Conditional Mandatory Fields ---

    residential_status: function(frm) {
        toggle_statutory_mandatory(frm);
    },

    salary_currency: function(frm) {
        toggle_swift_mandatory(frm);
        autopopulate_account_name(frm);
    },

    relieving_date: function(frm) {
        toggle_relieving_fields(frm);
    },

    leave_encashed: function(frm) {
        toggle_encashment_date(frm);
    },

    reason_for_leaving: function(frm) {
        toggle_resignation_letter(frm);
    },

    // --- Autopopulate Fields ---

    date_of_birth: function(frm) {
        if (frm.doc.date_of_birth) {
            let dob = frappe.datetime.str_to_obj(frm.doc.date_of_birth);
            let retirement = new Date(dob);
            retirement.setFullYear(retirement.getFullYear() + 60);
            frm.set_value('date_of_retirement', frappe.datetime.obj_to_str(retirement));
        }
    },

    employee: function(frm) {
        if (frm.doc.employee && !frm.doc.attendance_device_id) {
            frm.set_value('attendance_device_id', frm.doc.employee);
        }
    },

    employee_name: function(frm) {
        autopopulate_account_name(frm);
    },

    department: function(frm) {
        if (frm.doc.department) {
            frappe.db.get_value('Department', frm.doc.department, 'custom_department_appraisal_template', function(r) {
                if (r && r.custom_department_appraisal_template) {
                    if (!frm.doc.custom_department_appraisal_template) {
                        frm.set_value('custom_department_appraisal_template', r.custom_department_appraisal_template);
                    }
                }
            });
        }
    },

    // --- Refresh: ensure all conditional states are correct on load ---

    refresh: function(frm) {
        toggle_statutory_mandatory(frm);
        toggle_swift_mandatory(frm);
        toggle_relieving_fields(frm);
        toggle_encashment_date(frm);
        toggle_resignation_letter(frm);
    }
});

// ============================================================
// HELPER FUNCTIONS
// ============================================================

function toggle_statutory_mandatory(frm) {
    let is_resident = (frm.doc.residential_status == 'Resident');

    if (frm.fields_dict['tax_id']) {
        frm.set_df_property('tax_id', 'reqd', is_resident ? 1 : 0);
    }
    if (frm.fields_dict['shif_no']) {
        frm.set_df_property('shif_no', 'reqd', is_resident ? 1 : 0);
    }
}

function toggle_swift_mandatory(frm) {
    let is_usd = (frm.doc.salary_currency == 'USD');

    if (frm.fields_dict['swift_code']) {
        frm.set_df_property('swift_code', 'reqd', is_usd ? 1 : 0);
    }
}

function toggle_relieving_fields(frm) {
    let has_relieving = !!frm.doc.relieving_date;

    if (frm.fields_dict['leave_encashed']) {
        frm.set_df_property('leave_encashed', 'reqd', has_relieving ? 1 : 0);
    }
    if (frm.fields_dict['resignation_letter_date']) {
        frm.set_df_property('resignation_letter_date', 'reqd', has_relieving ? 1 : 0);
    }
}

function toggle_encashment_date(frm) {
    let has_relieving = !!frm.doc.relieving_date;
    let is_encashed = (frm.doc.leave_encashed == 'Yes');

    if (frm.fields_dict['encashment_date']) {
        frm.set_df_property('encashment_date', 'reqd', (has_relieving && is_encashed) ? 1 : 0);
    }
}

function toggle_resignation_letter(frm) {
    let is_resignation = (frm.doc.reason_for_leaving == 'Resignation');

    if (frm.fields_dict['resignation_letter']) {
        frm.set_df_property('resignation_letter', 'reqd', is_resignation ? 1 : 0);
    }
}

function autopopulate_account_name(frm) {
    if (frm.doc.salary_currency == 'KES' && frm.doc.employee_name) {
        if (!frm.doc.custom_account_name) {
            frm.set_value('custom_account_name', frm.doc.employee_name);
        }
    }
}
