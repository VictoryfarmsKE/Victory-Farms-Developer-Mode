frappe.ui.form.on('Certificate of Analysis', {
    onload(frm) {
        frm.analysis_templates = {
            "Whole, Gutted Tilapia": [
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
                        "Convex (Bulging) with protruding lens, transparent eye cap",
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
            ],

            "Tilapia Fillet": [
                {
                    physical_attribute: "General Appearance",
                    specification: "Clean, wholesome and characteristic of frozen tilapia fillet; uniform in appearance",
                    test_results: [
                        "Clean, wholesome and uniform in appearance"
                    ]
                },
                {
                    physical_attribute: "Colour",
                    specification: "Natural characteristic colour of tilapia flesh; free from abnormal discolouration or excessive browning",
                    test_results: [
                        "Natural characteristic colour; no abnormal discolouration observed"
                    ]
                },
                {
                    physical_attribute: "Odour",
                    specification: "Characteristic and free from sour, rancid or other objectionable odours upon thawing",
                    test_results: [
                        "Fresh and characteristic; no objectionable odour detected upon thawing"
                    ]
                },
                {
                    physical_attribute: "Texture",
                    specification: "Firm and characteristic of tilapia flesh upon thawing; free from excessive softness or mushiness",
                    test_results: [
                        "Firm and characteristic texture observed upon thawing"
                    ]
                },
                {
                    physical_attribute: "Surface Condition",
                    specification: "Free from excessive dehydration, freezer burn and abnormal surface discolouration",
                    test_results: [
                        "No excessive dehydration, freezer burn or abnormal surface discolouration observed"
                    ]
                },
                {
                    physical_attribute: "Skin",
                    specification: "Skinless",
                    test_results: [
                        "Skinless"
                    ]
                },
                {
                    physical_attribute: "Bones and Foreign Matter",
                    specification: "Free from objectionable bones and visible foreign matter",
                    test_results: [
                        "No objectionable bones or visible foreign matter observed"
                    ]
                },
                {
                    physical_attribute: "Physical Defects",
                    specification: "Free from significant tears, bruising or other defects affecting product quality",
                    test_results: [
                        "No significant physical defects observed"
                    ]
                }
            ]
        };

        // Load initial template
        load_analysis(frm);
    },

    product_description(frm) {
        load_analysis(frm);
    }
});


function load_analysis(frm) {
    const template =
        frm.analysis_templates?.[frm.doc.product_description] || [];

    frm.clear_table('analysis');

    template.forEach(row => {
        frm.add_child('analysis', {
            physical_attributes: row.physical_attribute,
            specification: row.specification,
            test_results: row.test_results[0]
        });
    });

    frm.refresh_field('analysis');
}


frappe.ui.form.on('CoA Analysis', {
    form_render(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        const template =
            frm.analysis_templates?.[frm.doc.product_description] || [];

        const attr = template.find(
            a => a.physical_attribute === row.physical_attributes
        );

        if (!attr) return;

        const grid = frm.fields_dict.analysis.grid;
        const rowForm = grid.grid_rows_by_docname[cdn]?.grid_form;

        if (!rowForm) return;

        const field = rowForm.fields_dict.test_results;
        field.df.options = attr.test_results.join('\n');
        field.refresh();
    }
});
