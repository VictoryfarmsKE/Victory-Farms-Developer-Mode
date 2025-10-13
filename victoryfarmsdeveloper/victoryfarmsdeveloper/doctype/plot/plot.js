// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt


frappe.ui.form.on('Plot', {
    async google_map_link(frm) {
        const link = frm.doc.google_map_link;
        if (!link) return;
        if (link.includes('maps.app.goo.gl')) {
            frappe.call({
                method: 'victoryfarmsdeveloper.victoryfarmsdeveloper.doctype.plot.plot.resolve_google_maps_link',
                args: { short_url: link },
                callback: function(r) {
                    if (r.message && r.message.lat && r.message.lng) {
                        frm.set_value('lat_location', r.message.lat);
                        frm.set_value('long_location', r.message.lng);
                        frappe.show_alert({
                            message: __('Coordinates extracted successfully.'),
                            indicator: 'green'
                        });
                    } else {
                        frappe.show_alert({
                            message: __('Unable to resolve short Google Maps link.'),
                            indicator: 'red'
                        });
                    }
                }
            });
        } else {
            // Handle standard full URLs
            const match = link.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
            if (match) {
                frm.set_value('lat_location', match[1]);
                frm.set_value('long_location', match[2]);
                frappe.show_alert({
                    message: __('Coordinates extracted from Google Maps link.'),
                    indicator: 'green'
                });
            } else {
                frappe.show_alert({
                    message: __('Invalid Google Maps link format.'),
                    indicator: 'red'
                });
            }
        }
    },


    refresh(frm) {
        if (frm.doc.lat_location && frm.doc.long_location) {
            frm.add_custom_button(__('View on Map'), () => {
                const url = `https://www.google.com/maps?q=${frm.doc.lat_location},${frm.doc.long_location}`;
                window.open(url, '_blank');
            });
        }
    }
});
