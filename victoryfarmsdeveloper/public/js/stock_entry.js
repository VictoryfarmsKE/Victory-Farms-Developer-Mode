frappe.ui.form.on('Stock Entry', {
    custom_pack_to_crates(frm){
        frappe.call({
            method: 'update_crates',
            doc: frm.doc,
            btn: $('.primary-action'),
            freeze: true,
            callback: (r) => {
                if (r.message) {
                    let response = r.message;
                    console.log(response);
                    refresh_field("custom_crates");
                } else {
                    console.error("No message returned from the server.");
                }
            }
        });
    }
});