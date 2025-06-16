// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt

frappe.ui.form.on('Certificate of Analysis', {
	onload: function(frm) {
		// Filter QC Personnel by department and status
		frm.set_query('qc_personnel', function() {
			return {
				filters: {
					'department': 'Quality Assurance - VFL',
					'status': 'Active'
				}
			};
		});
		frm.set_query('destination', function() {
			return {
				filters: {
					'warehouse_type': ['!=', 'Transit']
				}
			};
		});

		// Add attributes to analysis table
		frm.clear_table('analysis');
		const attributes = [
			{ physical_attribute: "Appearance", specification: "Shiny, Bright, Iridescent" },
			{ physical_attribute: "Odor", specification: "Natural Seaweed" },
			{ physical_attribute: "Color of Gills", specification: "Bright, red" },
			{ physical_attribute: "Body Texture", specification: "Firm and elastic" },
			{ physical_attribute: "Eye", specification: "Clear and bulging" },
			{ physical_attribute: "Slime", specification: "Clear, Transparent" }
		];

		attributes.forEach(attr => {
			frm.add_child('analysis', {
				physical_attributes: attr.physical_attribute,
				specification: attr.specification
			});
		});

		frm.refresh_field('analysis');
	}
});
