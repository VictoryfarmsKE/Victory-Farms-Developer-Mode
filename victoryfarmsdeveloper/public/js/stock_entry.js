frappe.ui.form.on('Stock Entry', {
    custom_pack_to_crates(frm){
        frappe.call({
            method: 'update_crates',
            doc: frm.doc,
            btn: $('.primary-action'),
            freeze: true,
            callback: (r) => {
                let response = r.message
                console.log(response)
                refresh_field("custom_crates")
            }
        })
    },
    custom_get_weights: function (frm, cnd, cdt) {
            console.log('response')
            $.ajax({
                type: 'POST',
                url: "http:localhost:5000/get_weight_scale",
                data: {},
                success: function (data, status, xhr) {
                    if (data.error == '') {
                        $.each(frm.doc.items || [], function (i, v) {
                            if (cdt == v.name) {
                                var amount = parseFloat(data.data)
                                frappe.model.set_value(v.doctype, v.name, "qty", amount)
                            }
    
                        })
                    }
    
                },
                error: function (xhr, status, error) {
                    console.error(xhr);
                    console.error(status);
                    console.error(error);
                }
            });
        }
});


