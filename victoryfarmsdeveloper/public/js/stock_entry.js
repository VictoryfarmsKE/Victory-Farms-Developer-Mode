frappe.ui.form.on('Stock Entry', {
    custom_pack_to_crates(frm){
        frappe.call({
            method: 'update_child_table',
            doc: frm.doc,
            btn: $('.primary-action'),
            freeze: true,
            callback: (r) => {
                let response = r.message
                console.log(response)
                refresh_field("custom_crates")
            }
        })
    }
});

