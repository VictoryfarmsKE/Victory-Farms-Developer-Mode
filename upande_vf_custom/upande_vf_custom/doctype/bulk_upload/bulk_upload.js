// Copyright (c) 2024, Upande Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Upload', {
	get_draft_payments(frm) {
        frappe.call({
            method: 'get_pending_payments',
            doc: frm.doc,
            btn: $('.primary-action'),
            freeze: true,
            callback: (r) => {
                if (r.message) {
                    if(frm.doc.type=="EFT"){
                        processEFTDraftPayments(frm, r.message.draft_payments);
                    }else if(frm.doc.type=="RTGS"){
                        processRTGSDraftPayments(frm, r.message.draft_payments, r.message.total_grand_total);
                    }
                    else if(frm.doc.type=="International Payments"){
                        processIPDraftPayments(frm, r.message.draft_payments, r.message.total_grand_total);
                    }
                    else if(frm.doc.type=="Mpesa"){
                        processMpesaDraftPayments(frm, r.message.draft_payments, r.message.total_grand_total);
                    }
                    
                    
                } else {
                    console.log("No Draft Payments Match The Criteria.");
                }
            },
            error: (r) => {
                console.error("Error", r);
                // Handle the error here
            }
        })
    },
    
    download(frm) {
        frappe.call({
            method: 'download_report',
            doc: frm.doc,
            callback: function(r) {
                if(r.message) {
                    window.open(r.message);
                }
            }
        });
        
    }
});


function processEFTDraftPayments(frm, draftPymnts) {
    const childTableField = 'eft_bulk_upload_items';

    const existingPymnts = new Set(frm.doc[childTableField].map(row => row.payment_reference)); 
    draftPymnts.forEach(dp => {
         if (!existingPymnts.has(dp.name)) {
            let newRow = frm.add_child(childTableField);
            newRow.payment_reference = dp.name; 
            newRow.beneficiary_name = dp.party;
            newRow.bank_account = dp.party_bank_account;
            newRow.reference = dp.reference_no
            newRow.bank = dp.bank_name
            newRow.amount = dp.paid_amount;
            existingPymnts.add(dp.name);
        }
    });
        
    frm.refresh_field(childTableField); 
    frm.save()
}

function processRTGSDraftPayments(frm, draftPymnts) {
    const childTableField = 'rtgs_bulk_upload_items'; 

    const existingPymnts = new Set(frm.doc[childTableField].map(row => row.payment_reference));
    draftPymnts.forEach(dp => {
         if (!existingPymnts.has(dp.name)) {
            let newRow = frm.add_child(childTableField);
            newRow.payment_reference = dp.name; 
            newRow.beneficiary_name = dp.party;
            newRow.bank_account = dp.party_bank_account;
            newRow.reference = dp.reference_no
            newRow.bank = dp.bank_name
            newRow.amount = dp.paid_amount;
            existingPymnts.add(dp.name);
        }
    });
    
    
    frm.refresh_field(childTableField); 
    frm.save()
}

function processIPDraftPayments(frm, draftPymnts, grand_totals) {
    const childTableField = 'international_payments_bulk_upload_items'; // Update this with the actual field name of your child table

    // Create a set of existing entries to check for duplicates
    const existingPymnts = new Set(frm.doc[childTableField].map(row => row.payment_reference)); // Assuming 'payment_reference' is a field in the child table
    draftPymnts.forEach(dp => {
         if (!existingPymnts.has(dp.name)) {
            let newRow = frm.add_child(childTableField);
            newRow.payment_reference = dp.name;
            newRow.beneficiary_name = dp.party; 
            newRow.beneficiary_account = dp.bank_account;
            newRow.reference = dp.name;
            newRow.beneficiary_email_id = dp.contact_email;
            newRow.debit_amount = dp.paid_amount;
            newRow.swift_code = dp.swift_code;
            newRow.payment_type = dp.custom_upload_type;
            existingPymnts.add(dp.name); // Add the new purchase order to the set of existing orders
        }
    });
    
    frm.doc.total_amount = grand_totals
    
    frm.refresh_field(childTableField); // Refresh the child table field to display the added rows
    frm.refresh_field('total_amount')
    frm.save()
}
function processMpesaDraftPayments(frm, draftPymnts, grand_totals) {
    const childTableField = 'mpesa_bulk_upload_items';

    // Create a set of existing entries to check for duplicates
    const existingPymnts = new Set(frm.doc[childTableField].map(row => row.payment_reference));
    draftPymnts.forEach(dp => {
         if (!existingPymnts.has(dp.name)) {
            let newRow = frm.add_child(childTableField);
            newRow.payment_reference = dp.name;
            newRow.beneficiary_name = dp.party;
            newRow.bank_account = dp.bank_name;
            newRow.reference = dp.reference_no;
            newRow.amount = dp.paid_amount;
            // Populate beneficiary details from Payment Entry's
            // custom_beneficiaries (fetched server-side)
            newRow.mobilenumber = dp.mobilenumber || '';
            newRow.documenttype = dp.documenttype || '';
            newRow.supplier_invoice = dp.supplier_invoice || '';
            newRow.purposeofpayment = dp.purposeofpayment || '';
            existingPymnts.add(dp.name);
        }
    });
    
    frm.doc.total_amount = grand_totals
    
    frm.refresh_field(childTableField);
    frm.refresh_field('total_amount')
    frm.save()
}
