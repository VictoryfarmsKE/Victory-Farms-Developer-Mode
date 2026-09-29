// Processing Line is only recorded on harvesting and processing at SUVAC.
const PROCESSING_LINE_TYPES = ["Harvesting of Fish", "Fish Processing SUVAC"];

function toggle_processing_line(frm) {
    const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
    if (!grid || !frappe.meta.has_field("Stock Entry Detail", "custom_line")) return;

    const hidden = PROCESSING_LINE_TYPES.includes(frm.doc.stock_entry_type) ? 0 : 1;
    grid.update_docfield_property("custom_line", "hidden", hidden);
    grid.update_docfield_property("custom_line", "in_list_view", hidden ? 0 : 1);
    grid.reset_grid();
}

// Processing -> blast freezer (truck warehouse) -> cold room (destination).
const BLAST_TRANSFER = "Fish Transfer from Processing to SUVAC Blast";
const BLAST_WAREHOUSES = {
    from_warehouse: "KPC-02-SUV-120MT - VFL",
    to_warehouse: "SUVAC Blast - VFL",
    destination_warehouse: "SUVAC Cold Room - VFL",
};

function set_blast_warehouses(frm) {
    if (frm.doc.stock_entry_type !== BLAST_TRANSFER || frm.doc.docstatus !== 0) return;

    Object.entries(BLAST_WAREHOUSES).forEach(([field, warehouse]) => {
        if (!frm.doc[field]) frm.set_value(field, warehouse);
    });
}

frappe.ui.form.on('Stock Entry', {
    refresh(frm) {
        toggle_processing_line(frm);
    },
    stock_entry_type(frm) {
        toggle_processing_line(frm);
        set_blast_warehouses(frm);
    },
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
