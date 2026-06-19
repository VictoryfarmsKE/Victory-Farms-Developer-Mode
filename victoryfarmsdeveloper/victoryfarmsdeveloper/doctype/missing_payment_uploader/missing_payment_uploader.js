// Copyright (c) 2026, Victory Farms and Contributors
// License: MIT. See LICENSE

frappe.ui.form.on("Missing Payment Uploader", {
  refresh(frm) {
    // Show Process Payments button when file is attached and status is Draft or Failed
    if (
      frm.doc.payment_file &&
      (frm.doc.status === "Draft" || frm.doc.status === "Failed")
    ) {
      frm.add_custom_button(
        __("Process Payments"),
        function () {
          frappe.confirm(
            __(
              "This will read the Excel file and create Mpesa Payment Register records for each row. Continue?"
            ),
            function () {
              // User confirmed
              process_payments(frm);
            }
          );
        },
        __("Actions")
      ).addClass("btn-primary-dark");
    }

    // Show Re-upload button when completed
    if (
      frm.doc.status === "Completed" &&
      frm.doc.payment_file
    ) {
      frm.add_custom_button(
        __("Re-upload & Process Again"),
        function () {
          frm.set_value("status", "Draft");
          frm.set_value("result_log", "");
          frm.set_value("total_rows", 0);
          frm.set_value("success_count", 0);
          frm.set_value("failure_count", 0);
          frm.save();
        },
        __("Actions")
      );
    }
  },
});

function process_payments(frm) {
  // Disable the button and show loading
  frm.disable_save();
  frm.set_value("status", "Processing");
  frm.save().then(() => {
    frappe.show_alert({
      message: __("Processing Excel file... Please wait."),
      indicator: "blue",
    });

    frm.call("process_payments", {}, function (r) {
      frm.enable_save();

      if (r.message) {
        frm.reload_doc();

        if (r.message.success) {
          frappe.show_alert({
            message: __(
              `Import complete! ${r.message.imported} of ${r.message.total} records imported successfully.`
            ),
            indicator: "green",
          });

          if (r.message.failed > 0) {
            frappe.msgprint({
              title: __("Import Completed with Errors"),
              message: __(
                `${r.message.failed} records failed. Check the Result Log for details.`
              ),
              indicator: "orange",
            });
          }
        } else {
          frappe.show_alert({
            message: __("Import failed. Check the Result Log for details."),
            indicator: "red",
          });
        }
      } else {
        frappe.show_alert({
          message: __("Unexpected response. Please try again."),
          indicator: "red",
        });
      }
    });
  });
}