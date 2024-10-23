frappe.ui.form.on('Stock Entry', {
    onload: function(frm) {
        console.log('Custom onload logic');
    },
    custom_pack_to_crates(frm){
        frappe.call({
            method: 'victoryfarmsdeveloper.victoryfarmsdeveloper.customization.doctype.stock_entry.stock_entry.update_child_table',
            args: {
                doc: frm.doc
            },
            freeze: true,
            callback: function(r) {
                console.log('Server response received');
                if (r.message) {
                    console.log(r.message);
                    frm.refresh_field("crates");
                } else {
                    console.log('No message returned from the server.');
                }
            },
            error: function(err) {
                console.error("Error calling method:", err);
            }
        });
    }
});

