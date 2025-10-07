// Copyright (c) 2025, Christine K and contributors
// For license information, please see license.txt


frappe.ui.form.on('Plot', {
    google_map_link: function(frm) {
        const link = frm.doc.google_map_link;
        if (!link) return;
        const match = link.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
        
        if (match) {
            const lat = match[1];
            const lng = match[2];
            frm.set_value('lat_location', lat);
            frm.set_value('long_location', lng);
            frappe.show_alert({
                message: __('Latitude and Longitude extracted from Google Maps link.'),
                indicator: 'green'
            });
        } else {
            frappe.show_alert({
                message: __('Could not extract coordinates. Check link format.'),
                indicator: 'red'
            });
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
