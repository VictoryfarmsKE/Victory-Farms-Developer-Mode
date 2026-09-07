frappe.ui.form.on("Weighbridge Reading", {
	setup(frm) {
		frm.set_query("truck", () => {
			return { filters: { warehouse_type: "Transit", is_group: 0 } };
		});
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.reading_time) {
			frm.set_value("reading_time", frappe.datetime.now_datetime());
		}
	},
});
