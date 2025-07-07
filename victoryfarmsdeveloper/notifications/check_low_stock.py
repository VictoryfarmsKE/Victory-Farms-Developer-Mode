import frappe
from datetime import datetime
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
import json

@frappe.whitelist()
def check_low_stock():
    item_code = "Cement in 50KG bags"
    warehouse = "Consumables Store - VFL"
    
    # Get the current date & time
    now = datetime.now()
    posting_date = now.strftime("%Y-%m-%d")
    posting_time = now.strftime("%H:%M:%S")

    # Fetch stock balance
    stock_data = get_stock_balance_for(item_code, warehouse, posting_date, posting_time)
    
    stock_qty = stock_data.get("qty", 0)

    if stock_qty <= 300:
        # Notify users if stock is low
        recipients = [user.email for user in frappe.get_all("User", filters={"role": "Store Assistant"}, fields=["email"])]

        subject = "⚠️ Low Stock Alert: Cement in 50KG bags"
        message = f"Item Cement in 50KG bags stock is at {stock_qty} units in Consumables Store - VFLupdate. Please restock!"
     
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            now=True,
        )
    else:
        # frappe.log_error(f"Stock is sufficient ({stock_qty}), no notification needed.")
        return {
            "status": "success",
            "message": f"Stock is sufficient ({stock_qty}), no notification needed."
        }

def check_branch_low_stock():
    frappe.log_error("check_branch_low_stock triggered", "Low Stock DEBUG")

    try:
        RECIPIENTS = {
            "South America - VFL": ["merving@victoryfarmskenya.com"],
            "Antarctica - VFL": ["teresiak@victoryfarmskenya.com"],
            "North America - VFL": ["winniea@victoryfarmskenya.com"],
            "Europe - VFL": ["evans.otieno@victoryfarmskenya.com"],
            "Asia - VFL": ["jemutair@victoryfarmskenya.com"],
            "Africa - VFL": ["perezk@victoryfarmskenya.com"],
            "Victory Fresh": ["josephw@victoryfarmskenya.com"],
        }
        
        ALWAYS_RECIPIENTS = [
            "cynthiar@victoryfarmskenya.com",  # Sales Director
            "stephennj@victoryfarmskenya.com"  # Regional Sales Manager
        ]
        
        SMS_RECIPIENTS = {
            "South America - VFL": "+254704926558",
            "Antarctica - VFL": "+254799416393",
            "North America - VFL": "+254795959395",
            "Europe - VFL": "+254111996178",
            "Asia - VFL": "+254113789815",
            "Africa - VFL": "+254793453554",
            "Victory Fresh - VFL": "+254746760913"
        }

        SMS_ALWAYS_RECIPIENTS = [
            "+254113574233",  # Sales Director
            "+254 711810457",  # Regional Sales Manager
        ]

        ITEM_CODES = ["Large Size", "Medium Size", "Small Size"]
        MIN_STOCK_THRESHOLD = 50

        now = datetime.now()
        posting_date = now.strftime("%Y-%m-%d")
        posting_time = now.strftime("%H:%M:%S")

        try:
            allowed_parents = [
                "South America - VFL",
                "Antarctica - VFL",
                "North America - VFL",
                "Europe - VFL",
                "Asia - VFL",
                "Africa - VFL",
                "Victory Fresh - VFL"
            ]

            branches = frappe.get_all(
                "Warehouse",
                filters={
                    "warehouse_type": "Branch",
                    "parent_warehouse": ["in", allowed_parents]
                },
                fields=["name", "parent_warehouse"]
            )
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Failed to fetch Branch Warehouses")
            return

        for branch in branches:
            try:
                branch_name = branch["name"]
                parent_warehouse = branch.get("parent_warehouse", "").strip()

                if parent_warehouse not in allowed_parents:
                    continue
                
                low_stock_items = []

                for item_code in ITEM_CODES:
                    try:
                        stock_balance = get_stock_balance_for(item_code, branch_name, posting_date, posting_time)
                        qty = stock_balance.get("qty", 0)

                        if qty <= MIN_STOCK_THRESHOLD:
                            low_stock_items.append(f"{item_code} (Qty: {qty})")
                    except Exception as e:
                        frappe.log_error(
                            frappe.get_traceback(),
                            f"Stock fetch failed for Item: {item_code} in Branch: {branch_name}"
                        )

                if low_stock_items:
                    subject = f"⚠️ Low Stock Alert at {branch_name}"
                    message = (
                        f"Hello,<br><br>Be informed that branch {branch_name} is below the minimum stock 50 Kg stock for size:<br><br>"
                        f"Please submit an order for a stock up from VLC as soon as possible<br>" 
                        + "<br>".join(low_stock_items)
                    ) 
                    parent_key = parent_warehouse.strip()
                    branch_specific = RECIPIENTS.get(parent_key, [])
                    recipients = list(ALWAYS_RECIPIENTS)
                    recipients.extend(branch_specific)
                    recipients = list(set(recipients)) 
                    
                    sms_message = f"Be informed that branch {branch_name} is below the 50kg minimum stock. Please submit an order for a stock up from VLC as soon as possible. <br/> " + ", ".join(low_stock_items)

                    # Get SMS recipients
                    sms_recipients = list(SMS_ALWAYS_RECIPIENTS)
                    sms_branch_recipient = SMS_RECIPIENTS.get(parent_key)
                    if sms_branch_recipient:
                        sms_recipients.append(sms_branch_recipient)

                    # Deduplicate
                    sms_recipients = list(set(sms_recipients))

                    # Send SMS to each number
                    for mobile_no in sms_recipients:
                        try:
                            response = frappe.call(
                                "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings.send_sms",
                                receiver_list=json.dumps([mobile_no]),
                                msg=sms_message
                            )
                            if response:
                                try:
                                    response_json = json.loads(response)
                                    frappe.log_error(str(response_json), f"SMS Sent to {mobile_no}")
                                except json.JSONDecodeError as e:
                                    frappe.log_error(f"Invalid JSON response for {mobile_no}: {e}", "SMS Sending Error")
                        except Exception:
                            frappe.log_error(
                                frappe.get_traceback(),
                                f"Failed to send SMS to {mobile_no} for branch {branch_name}"
                            )


                    try:
                        frappe.sendmail(
                            recipients=branch_specific,
                            cc=ALWAYS_RECIPIENTS,
                            bcc="christinek@victoryfarmskenya.com",
                            subject=subject,
                            message=message,
                            expose_recipients="header",
                            now=True
                        )
                    except Exception as e:
                        frappe.log_error(
                            frappe.get_traceback(),
                            f"Failed to send email for branch {branch_name}"
                        )
            except Exception as e:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Error processing branch {branch.get('name', 'unknown')}"
                )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Unexpected error in check_branch_low_stock")
