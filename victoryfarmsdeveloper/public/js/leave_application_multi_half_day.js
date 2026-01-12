/**
 * Multiple Half Days Feature - Client Side Implementation
 * ========================================================
 * 
 * This script extends the Leave Application form to support selecting
 * multiple half days in a single leave application.
 * 
 * Features:
 * - Shows a child table when half_day is checked (for multi-day leaves)
 * - Validates dates are within leave period
 * - Calculates total leave days with multiple half days
 * - Provides "Select All" and "Clear All" quick actions
 */

frappe.ui.form.on("Leave Application", {
    setup: function(frm) {
        // Set query for half_day_dates child table to only allow dates within range
        frm.set_query("half_day_date", "half_day_dates", function() {
            return {
                filters: {}
            };
        });
    },

    refresh: function(frm) {
        // Add custom buttons for half day management
        if (frm.doc.docstatus === 0 && frm.doc.half_day && frm.doc.from_date && frm.doc.to_date) {
            frm.trigger("add_half_day_buttons");
        }
        
        // Show info about multiple half days feature
        if (frm.doc.half_day && frm.doc.half_day_dates && frm.doc.half_day_dates.length > 0) {
            frm.dashboard.add_comment(
                __("Multiple Half Days: {0} day(s) selected as half day", [frm.doc.half_day_dates.length]),
                "blue",
                true
            );
        }
    },

    half_day: function(frm) {
        if (frm.doc.half_day) {
            // Check if it's a single day leave
            if (frm.doc.from_date === frm.doc.to_date) {
                // Single day - auto populate half_day_dates with from_date
                frm.clear_table("half_day_dates");
                let row = frm.add_child("half_day_dates");
                row.half_day_date = frm.doc.from_date;
                frm.refresh_field("half_day_dates");
                
                // Also set legacy field for compatibility
                frm.set_value("half_day_date", frm.doc.from_date);
            } else {
                // Multi-day leave - show dialog to select dates
                frm.trigger("show_half_day_selector");
            }
        } else {
            // Clear half day data
            frm.clear_table("half_day_dates");
            frm.refresh_field("half_day_dates");
            frm.set_value("half_day_date", "");
        }
        
        frm.trigger("calculate_total_days_multi");
    },

    from_date: function(frm) {
        frm.trigger("validate_half_day_dates");
        frm.trigger("calculate_total_days_multi");
    },

    to_date: function(frm) {
        frm.trigger("validate_half_day_dates");
        frm.trigger("calculate_total_days_multi");
    },

    add_half_day_buttons: function(frm) {
        // Only for multi-day leaves
        if (frm.doc.from_date === frm.doc.to_date) return;
        
        frm.add_custom_button(__("Select Half Days"), function() {
            frm.trigger("show_half_day_selector");
        }, __("Actions"));
    },

    show_half_day_selector: function(frm) {
        if (!frm.doc.from_date || !frm.doc.to_date || !frm.doc.employee || !frm.doc.leave_type) {
            frappe.msgprint(__("Please select Employee, Leave Type, From Date and To Date first"));
            return;
        }

        // Get valid dates for half day selection
        frappe.call({
            method: "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.multiple_half_days.get_valid_dates_for_half_day",
            args: {
                employee: frm.doc.employee,
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                leave_type: frm.doc.leave_type
            },
            callback: function(r) {
                if (r.message) {
                    frm.trigger("render_half_day_dialog", r.message);
                }
            }
        });
    },

    render_half_day_dialog: function(frm, valid_dates) {
        // Get currently selected dates
        let selected_dates = new Set();
        if (frm.doc.half_day_dates) {
            frm.doc.half_day_dates.forEach(row => {
                if (row.half_day_date) {
                    selected_dates.add(row.half_day_date);
                }
            });
        }

        // Build checkbox HTML
        let checkboxes_html = `
            <div class="half-day-selector" style="max-height: 400px; overflow-y: auto;">
                <div class="mb-3">
                    <button class="btn btn-xs btn-default select-all-btn">${__("Select All")}</button>
                    <button class="btn btn-xs btn-default clear-all-btn ml-2">${__("Clear All")}</button>
                </div>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th style="width: 50px;">${__("Select")}</th>
                            <th>${__("Date")}</th>
                            <th>${__("Day")}</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        valid_dates.forEach(date_str => {
            let date = frappe.datetime.str_to_obj(date_str);
            let day_name = frappe.datetime.get_day_name(date_str);
            let is_checked = selected_dates.has(date_str) ? "checked" : "";
            
            checkboxes_html += `
                <tr>
                    <td class="text-center">
                        <input type="checkbox" class="half-day-checkbox" 
                               data-date="${date_str}" ${is_checked}>
                    </td>
                    <td>${frappe.datetime.str_to_user(date_str)}</td>
                    <td>${day_name}</td>
                </tr>
            `;
        });

        checkboxes_html += `
                    </tbody>
                </table>
            </div>
        `;

        let dialog = new frappe.ui.Dialog({
            title: __("Select Half Day Dates"),
            fields: [
                {
                    fieldtype: "HTML",
                    fieldname: "half_day_selector",
                    options: checkboxes_html
                }
            ],
            primary_action_label: __("Apply"),
            primary_action: function() {
                let selected = [];
                dialog.$wrapper.find(".half-day-checkbox:checked").each(function() {
                    selected.push($(this).data("date"));
                });
                
                // Update child table
                frm.clear_table("half_day_dates");
                selected.forEach(date => {
                    let row = frm.add_child("half_day_dates");
                    row.half_day_date = date;
                });
                frm.refresh_field("half_day_dates");
                
                // Set legacy field for first date (compatibility)
                if (selected.length > 0) {
                    frm.set_value("half_day_date", selected[0]);
                } else {
                    frm.set_value("half_day_date", "");
                }
                
                frm.trigger("calculate_total_days_multi");
                dialog.hide();
                
                frappe.show_alert({
                    message: __("{0} half day(s) selected", [selected.length]),
                    indicator: "green"
                });
            }
        });

        dialog.show();

        // Add event handlers for select all / clear all
        dialog.$wrapper.find(".select-all-btn").on("click", function() {
            dialog.$wrapper.find(".half-day-checkbox").prop("checked", true);
        });

        dialog.$wrapper.find(".clear-all-btn").on("click", function() {
            dialog.$wrapper.find(".half-day-checkbox").prop("checked", false);
        });
    },

    validate_half_day_dates: function(frm) {
        if (!frm.doc.half_day_dates || frm.doc.half_day_dates.length === 0) return;
        if (!frm.doc.from_date || !frm.doc.to_date) return;

        let from_date = frappe.datetime.str_to_obj(frm.doc.from_date);
        let to_date = frappe.datetime.str_to_obj(frm.doc.to_date);
        let invalid_dates = [];

        frm.doc.half_day_dates.forEach((row, idx) => {
            if (row.half_day_date) {
                let hd_date = frappe.datetime.str_to_obj(row.half_day_date);
                if (hd_date < from_date || hd_date > to_date) {
                    invalid_dates.push(row.half_day_date);
                }
            }
        });

        if (invalid_dates.length > 0) {
            frappe.msgprint({
                title: __("Invalid Half Day Dates"),
                message: __("The following half day dates are outside the leave period and will be removed: {0}", 
                    [invalid_dates.join(", ")]),
                indicator: "orange"
            });

            // Remove invalid dates
            frm.doc.half_day_dates = frm.doc.half_day_dates.filter(row => {
                if (!row.half_day_date) return false;
                let hd_date = frappe.datetime.str_to_obj(row.half_day_date);
                return hd_date >= from_date && hd_date <= to_date;
            });
            frm.refresh_field("half_day_dates");
        }
    },

    calculate_total_days_multi: function(frm) {
        if (!frm.doc.from_date || !frm.doc.to_date || !frm.doc.employee || !frm.doc.leave_type) {
            return;
        }

        // Get half day dates from child table
        let half_day_dates = [];
        if (frm.doc.half_day && frm.doc.half_day_dates) {
            frm.doc.half_day_dates.forEach(row => {
                if (row.half_day_date) {
                    half_day_dates.push(row.half_day_date);
                }
            });
        }

        frappe.call({
            method: "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.multiple_half_days.get_number_of_leave_days_with_multi_half_days",
            args: {
                employee: frm.doc.employee,
                leave_type: frm.doc.leave_type,
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                half_day: frm.doc.half_day ? 1 : 0,
                half_day_dates: JSON.stringify(half_day_dates)
            },
            callback: function(r) {
                if (r.message !== undefined) {
                    frm.set_value("total_leave_days", r.message);
                }
            }
        });
    }
});

// Child table events
frappe.ui.form.on("Leave Application Half Day", {
    half_day_date: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Validate date is within range
        if (row.half_day_date && frm.doc.from_date && frm.doc.to_date) {
            let hd_date = frappe.datetime.str_to_obj(row.half_day_date);
            let from_date = frappe.datetime.str_to_obj(frm.doc.from_date);
            let to_date = frappe.datetime.str_to_obj(frm.doc.to_date);
            
            if (hd_date < from_date || hd_date > to_date) {
                frappe.msgprint(__("Half Day Date must be between {0} and {1}", 
                    [frm.doc.from_date, frm.doc.to_date]));
                frappe.model.set_value(cdt, cdn, "half_day_date", "");
                return;
            }
        }
        
        frm.trigger("calculate_total_days_multi");
    },
    
    half_day_dates_remove: function(frm) {
        frm.trigger("calculate_total_days_multi");
    }
});
