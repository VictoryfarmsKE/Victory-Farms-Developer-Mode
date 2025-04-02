import frappe
import json

def sales_invoice_status_change(doc, method):
    # Get the document's state
    previous_doc = doc.get_doc_before_save()
    previous_status = previous_doc.status if previous_doc else None
    
    # Check if a Payment Entry is linked to this Sales Invoice
    has_payment_entry = frappe.db.exists("Payment Entry Reference", {"reference_name": doc.name})

    if previous_status != "Paid" and doc.status == "Paid" and not doc.sms_sent and has_payment_entry:
        send_sms_notification(doc)
        frappe.db.set_value("Sales Invoice", doc.name, "sms_sent", 1)
        frappe.db.commit()


# def send_sms_notification(doc):
#     """ Sends an SMS when a Sales Invoice is marked as Paid. """
#     try:
#         text_items = ""
#         items = doc.get("items")

#         for item in items:
#             text_items += f'{item.item_code} - {item.qty} {item.uom} - {doc.currency} {frappe.utils.fmt_money(item.amount)}\n'

#         rounded_total_qty = round(float(doc.total_qty), 3)

#         customer_name = f'Name :: {doc.customer_name} <br />'
#         invoice_no = f'Order :: {doc.name} <br />'
#         invoice_date = f'Date :: {frappe.utils.format_date(doc.posting_date,)} <br />'
#         invoice_time = f'Time :: {frappe.utils.format_time(doc.posting_time)} <br />'
#         invoice_status = f'Status :: {doc.status} <br />'
#         pos_profile = f'You were served at :: {doc.pos_profile} <br />'
#         items_header = f'<br />Items :: <br />'
#         total_qty = f'<br />Total Qty :: {str(rounded_total_qty)}<br />'
#         total_amount = f'Grand Total :: {doc.currency} {frappe.utils.fmt_money(doc.rounded_total)}<br />'
#         terms_info1 = 'Pre-payment of goods is not allowed. <br />'
#         terms_info2 = 'All transactions are done in real-time. <br />'
#         terms_info3 = 'Always pay through the Victory Farms official till number.'
#         terms_info = f'{terms_info1}{terms_info2}{terms_info3}'

#         message = f'{customer_name}{invoice_no}{invoice_date}{invoice_time}{invoice_status}{pos_profile}{items_header}{text_items}{total_qty}{total_amount}{terms_info}'
#         message = message.replace('<br />', '\n')

#         # Format the mobile number
#         contact_mobile = doc.contact_mobile
#         if contact_mobile and contact_mobile.startswith('0'):
#             mobile_no = ['254' + contact_mobile[1:]]
#         else:
#             mobile_no = [contact_mobile]

#         if not mobile_no:
#             frappe.log_error(f"Invoice {doc.name}: No valid mobile number found.")
#             return

#         # Send SMS
#         response = frappe.call(
#             "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings.send_sms",
#             receiver_list=mobile_no,
#             msg=message
#         )
#     except Exception as e:
#         frappe.log_error(f"SMS error: {str(e)}")


def send_sms_notification(doc):
    """ Sends an SMS when a Sales Invoice is marked as Paid. """
    try:
        text_items = ""
        items = doc.get("items")

        for item in items:
            text_items += f'{item.item_code} - {item.qty} {item.uom} - {doc.currency} {frappe.utils.fmt_money(item.amount)}\n'

        rounded_total_qty = round(float(doc.total_qty), 3)

        # Check if customer has loyalty program
        loyalty_points_balance = 0
        if doc.customer:
            loyalty_entries = frappe.get_all(
                "Loyalty Point Entry",
                filters={
                    "customer": doc.customer,
                    "expiry_date": (">=", frappe.utils.today()),
                },
                group_by="company",
                fields=["sum(loyalty_points) as loyalty_points"],
                as_list=False
            )
            if loyalty_entries:
                loyalty_points_balance = sum(entry["loyalty_points"] or 0 for entry in loyalty_entries)

        # Basic invoice information
        customer_name = f'Name :: {doc.customer_name} <br />'
        invoice_no = f'Order :: {doc.name} <br />'
        invoice_date = f'Date :: {frappe.utils.format_date(doc.posting_date,)} <br />'
        invoice_time = f'Time :: {frappe.utils.format_time(doc.posting_time)} <br />'
        invoice_status = f'Status :: {doc.status} <br />'
        pos_profile = f'You were served at :: {doc.pos_profile} <br />'
        items_header = f'<br />Items :: <br />'
        total_qty = f'<br />Total Qty :: {str(rounded_total_qty)}<br />'
        total_amount = f'Grand Total :: {doc.currency} {frappe.utils.fmt_money(doc.rounded_total)}<br />'
        
        # Terms and conditions
        terms_info1 = 'Pre-payment of goods is not allowed. <br />'
        terms_info2 = 'All transactions are done in real-time. <br />'
        terms_info3 = 'Always pay through the Victory Farms official till number. <br />'
        terms_info = f'{terms_info1}{terms_info2}{terms_info3}'

        # Loyalty program information
        loyalty_program = ""
        loyalty_points_msg = ""
        if doc.loyalty_program:
            loyalty_program = f'<br />Loyalty Program :: {doc.loyalty_program} <br /><br />'
            loyalty_points_msg = f'Loyalty Points Balance :: {loyalty_points_balance} <br />'

        # Construct final message based on loyalty program status
        if doc.redeem_loyalty_points:
            message = (
                f'You have redeemed your {doc.loyalty_program} points for this order. <br /><br />'
                f'{customer_name}{invoice_date}{invoice_time}'
                f'Status :: Redeemed<br />{pos_profile}{items_header}{text_items}'
                f'for {doc.loyalty_points} points<br /><br />Total Qty :: {str(rounded_total_qty)}<br /><br />'
                f'Loyalty Points Balance :: {loyalty_points_balance}<br /><br />'
                f'Thank you - Victory Farms.'
            )
        else:
            base_message = f'{customer_name}{invoice_no}{invoice_date}{invoice_time}{invoice_status}{pos_profile}{items_header}{text_items}{total_qty}{total_amount}{terms_info}'
            message = base_message + loyalty_program + loyalty_points_msg if doc.loyalty_program else base_message

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

        # Send SMS
        response = frappe.call(
            "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings.send_sms",
            receiver_list=mobile_no,
            msg=message
        )
        
        if response:
            try:
                response_json = json.loads(response)
            except json.JSONDecodeError as e:
                frappe.log_error(f"Invalid JSON response: {e}")
        else:
            frappe.log_error("Empty response from send_sms")
            
    except Exception as e:
        frappe.log_error(f"SMS error: {str(e)}")