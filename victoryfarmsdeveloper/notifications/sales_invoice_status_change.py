import frappe

def sales_invoice_status_change(doc, method):
    # Get the document's state before the current save
    previous_doc = doc.get_doc_before_save()
    previous_status = previous_doc.status if previous_doc else None
    
    # Check if a Payment Entry is linked to this Sales Invoice
    has_payment_entry = frappe.db.exists("Payment Entry Reference", {"reference_name": doc.name})

    if previous_status != "Paid" and doc.status == "Paid" and not doc.sms_sent and has_payment_entry:
        send_sms_notification(doc)

        # Mark as SMS sent to avoid duplication
        frappe.db.set_value("Sales Invoice", doc.name, "sms_sent", 1)
        frappe.db.commit()


def send_sms_notification(doc):
    """ Sends an SMS when a Sales Invoice is marked as Paid. """
    try:
        # Construct the SMS message
        text_items = ""
        items = doc.get("items")

        for item in items:
            text_items += f'{item.item_code} - {item.qty} {item.uom} - {doc.currency} {frappe.utils.fmt_money(item.amount)}\n'

        rounded_total_qty = round(float(doc.total_qty), 3)

        customer_name = f'Name :: {doc.customer_name} <br />'
        invoice_no = f'Order :: {doc.name} <br />'
        invoice_date = f'Date :: {frappe.utils.format_date(doc.posting_date,)} <br />'
        invoice_time = f'Time :: {frappe.utils.format_time(doc.posting_time)} <br />'
        invoice_status = f'Status :: {doc.status} <br />'
        pos_profile = f'You were served at :: {doc.pos_profile} <br />'
        items_header = f'<br />Items :: <br />'
        total_qty = f'<br />Total Qty :: {str(rounded_total_qty)}<br />'
        total_amount = f'Grand Total :: {doc.currency} {frappe.utils.fmt_money(doc.rounded_total)}<br />'
        # receipt_link = f'<br /> Receipt Link :: {receipt_link}{doc.name} <br /><br />'
        terms_info1 = 'Pre-payment of goods is not allowed. <br />'
        terms_info2 = 'All transactions are done in real-time. <br />'
        terms_info3 = 'Always pay through the Victory Farms official till number.'
        terms_info = f'{terms_info1}{terms_info2}{terms_info3}'

        message = f'{customer_name}{invoice_no}{invoice_date}{invoice_time}{invoice_status}{pos_profile}{items_header}{text_items}{total_qty}{total_amount}{terms_info}'
        message = message.replace('<br />', '\n')

        # Format the mobile number
        contact_mobile = doc.contact_mobile
        if contact_mobile and contact_mobile.startswith('0'):
            mobile_no = ['254' + contact_mobile[1:]]
        else:
            mobile_no = [contact_mobile]

        if not mobile_no:
            frappe.log_error(f"Invoice {doc.name}: No valid mobile number found.")
            return

        # frappe.log_error(f"Sending SMS to {mobile_no}: {message}")

        # Send SMS
        response = frappe.call(
            "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings.send_sms",
            receiver_list=mobile_no,
            msg=message
        )

        frappe.log_error(f"SMS response: {response}")

    except Exception as e:
        frappe.log_error(f"SMS error: {str(e)}")