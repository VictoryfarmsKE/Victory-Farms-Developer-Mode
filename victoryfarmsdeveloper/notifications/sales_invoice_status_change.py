import frappe

def sales_invoice_status_change(doc, method):
    previous_status = frappe.db.get_value("Sales Invoice", doc.name, "status")

    # Log the status change for debugging
    frappe.log_error(f"Invoice {doc.name} changed from {previous_status} to {doc.status}, SMS Sent: {doc.sms_sent}")

    # Check if a Payment Entry is linked to this Sales Invoice
    has_payment_entry = frappe.db.exists("Payment Entry Reference", {"reference_name": doc.name})

    if previous_status != "Paid" and doc.status == "Paid" and not doc.sms_sent and has_payment_entry:
        frappe.log_error(f"Invoice {doc.name} is now Paid with Payment Entry. Sending SMS...")

        send_sms_notification(doc)

        # Mark as SMS sent to avoid duplication
        frappe.db.set_value("Sales Invoice", doc.name, "sms_sent", 1)
        frappe.db.commit()


def send_sms_notification(doc):
    """ Sends an SMS when a Sales Invoice is marked as Paid. """
    try:
        contact_mobile = doc.contact_mobile
        if contact_mobile and contact_mobile.startswith('0'):
            mobile_no = ['254' + contact_mobile[1:]]
        else:
            mobile_no = [contact_mobile]

        if not mobile_no:
            frappe.log_error(f"Invoice {doc.name}: No valid mobile number found.")
            return
        
        message = f"Your Invoice {doc.name} is now Paid. Thank you!"
        frappe.log_error(f"Sending SMS to {mobile_no}: {message}")

        # Send SMS
        response = frappe.call(
            "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings.send_sms",
            receiver_list=mobile_no,
            msg=message
        )

        frappe.log_error(f"SMS response: {response}")

    except Exception as e:
        frappe.log_error(f"SMS error: {str(e)}")
