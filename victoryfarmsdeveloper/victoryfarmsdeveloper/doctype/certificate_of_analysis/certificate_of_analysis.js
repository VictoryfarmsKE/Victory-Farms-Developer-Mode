frappe.ui.form.on('Certificate of Analysis', {
    onload(frm) {
        frm.attributes = [
            {
                physical_attribute: "General Appearance",
                specification: "Shiny, Bright, Iridescent",
                test_results: [
                    "Full bloom, right shining, iridescent",
                    "Slight dullness and loss of bloom",
                    "Definite dullness and loss of bloom",
                    "Reddish lateral line, dull, no bloom"
                ]
            },
            {
                physical_attribute: "Odor (Gills)",
                specification: "Natural Seaweed",
                test_results: [
                    "Natural",
                    "Faint / sour",
                    "Slight moderate sour",
                    "Moderate to strong sour"
                ]
            },
            {
                physical_attribute: "Color of Gills",
                specification: "Bright, red",
                test_results: [
                    "Slight pinkish red",
                    "Pinkish red to brownish",
                    "Brown or grey",
                    "Bleached color, thick yellow slime"
                ]
            },
            {
                physical_attribute: "Slime",
                specification: "Clear, Transparent",
                test_results: [
                    "Clear, transparent and uniformly spread",
                    "Becoming turbid, opaque and milky",
                    "Thick, yellowish or green color"
                ]
            },
            {
                physical_attribute: "Eye",
                specification: "Clear and bulging",
                test_results: [
                    "Slightly cloudy of lens and sunken",
                    "Dull, sunken, cloudy",
                    "Sunken eyes covered with yellow slime",
                    "Concave in the center, milky eye cap, grey pupil"
                ]
            },
            {
                physical_attribute: "Body Texture",
                specification: "Firm and elastic",
                test_results: [
                    "Firm and elastic",
                    "Moderately soft and some loss of elasticity",
                    "Some softening",
                    "Limp and floppy"
                ]
            }
        ];

        frm.clear_table('analysis');
        frm.attributes.forEach(a => {
            frm.add_child('analysis', {
                physical_attributes: a.physical_attribute,
                specification: a.specification,
                test_results: a.test_results[0]
            });
        });
        frm.refresh_field('analysis');
    }
});

frappe.ui.form.on('CoA Analysis', {
    form_render(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const attr = (frm.attributes || []).find(a => a.physical_attribute === row.physical_attributes);
        if (!attr) return;
        const gr = frm.fields_dict.analysis.grid;
        const rowForm = gr.grid_rows_by_docname[cdn]?.grid_form;
        if (!rowForm) return;

        const field = rowForm.fields_dict.test_results;
        field.df.options = attr.test_results.join('\n');
        field.refresh();

        if (!row.test_results) {
            frappe.model.set_value(cdt, cdn, 'test_results', attr.test_results[0]);
        }
    }
});
