frappe.ui.form.on('Payment Entry', {
    refresh(frm) {
        set_beneficiary_purpose(frm);
        add_upload_beneficiaries_button(frm);
    },
    validate(frm) {
        set_beneficiary_purpose(frm);
    }
});

frappe.ui.form.on('Payment Entry Reference', {
    reference_name(frm, cdt, cdn) {
        set_beneficiary_purpose(frm);
    },
    reference_doctype(frm, cdt, cdn) {
        set_beneficiary_purpose(frm);
    },
    references_add(frm, cdt, cdn) {
        set_beneficiary_purpose(frm);
    },
    references_remove(frm) {
        set_beneficiary_purpose(frm);
    }
});

function set_beneficiary_purpose(frm) {
    resolve_po_refs(frm).then((po_refs) => {
        const unique_refs = [...new Set(po_refs)];
        if (!unique_refs.length) return;

        const new_value = unique_refs.join(' | ');
        const first_po = unique_refs[0];

        // Auto-fill Reference Number with the first PO reference
        if (frm.doc.reference_no !== first_po) {
            frm.set_value('reference_no', first_po);
        }

        const rows = frm.doc.custom_beneficiaries || [];
        let changed = false;
        rows.forEach((row) => {
            if (row.purpose_of_payment !== new_value) {
                frappe.model.set_value(row.doctype, row.name, 'purpose_of_payment', new_value);
                changed = true;
            }
        });

        if (changed) {
            frm.refresh_field('custom_beneficiaries');
        }
    });
}

function resolve_po_refs(frm) {
    return new Promise((resolve) => {
        const references = frm.doc.references || [];
        const po_refs = [];
        const invoice_refs = [];

        references.forEach((r) => {
            if (!r.reference_name) return;

            if (r.reference_doctype === 'Purchase Order') {
                po_refs.push(r.reference_name);
            } else if (r.reference_doctype === 'Purchase Invoice') {
                invoice_refs.push(r.reference_name);
            }
        });

        if (!invoice_refs.length) {
            resolve(po_refs);
            return;
        }

        let pending = invoice_refs.length;
        invoice_refs.forEach((invoice_name) => {
            frappe.db.get_list('Purchase Invoice Item', {
                filters: { parent: invoice_name, purchase_order: ['is', 'set'] },
                fields: ['purchase_order'],
                distinct: true
            }).then((rows) => {
                rows.forEach((row) => {
                    if (row.purchase_order) po_refs.push(row.purchase_order);
                });
                pending -= 1;
                if (pending <= 0) resolve(po_refs);
            }).catch(() => {
                pending -= 1;
                if (pending <= 0) resolve(po_refs);
            });
        });
    });
}

function add_upload_beneficiaries_button(frm) {
    if (!frm.custom_upload_beneficiaries_button_added) {
        frm.add_custom_button(__('Upload Beneficiaries'), () => {
            upload_beneficiaries(frm);
        }, __('Beneficiary'));
        frm.custom_upload_beneficiaries_button_added = true;
    }
}

function upload_beneficiaries(frm) {
    new frappe.ui.FileUploader({
        allow_multiple: false,
        restrictions: {
            allowed_file_types: ['.xlsx', '.xls', '.csv']
        },
        on_success(file_doc) {
            if (!file_doc || !file_doc.file_url) {
                frappe.msgprint(__('Upload failed. Please try again.'));
                return;
            }

            frappe.call({
                method: 'victoryfarmsdeveloper.victoryfarmsdeveloper.customization.payment_entry.payment_entry.upload_beneficiaries',
                args: {
                    file_url: file_doc.file_url
                },
                callback(r) {
                    if (r.exc) {
                        frappe.msgprint(r.exc);
                        return;
                    }

                    const rows = r.message || [];
                    if (!rows.length) {
                        frappe.msgprint(__('No valid beneficiary rows found in the uploaded file.'));
                        return;
                    }

                    frm.clear_table('custom_beneficiaries');
                    rows.forEach((row) => {
                        const child = frm.add_child('custom_beneficiaries');
                        child.mobile_number = row.mobile_number;
                        child.document_type = row.document_type;
                        child.document_number = row.document_number;
                        child.amount = row.amount;
                        child.beneficiary_name = row.beneficiary_name;
                        child.purpose_of_payment = row.purpose_of_payment;
                    });

                    set_beneficiary_purpose(frm);
                    frm.refresh_field('custom_beneficiaries');
                    frappe.show_alert({
                        message: __('{0} beneficiary rows imported.', [rows.length]),
                        indicator: 'green'
                    });
                }
            });
        }
    });
}
