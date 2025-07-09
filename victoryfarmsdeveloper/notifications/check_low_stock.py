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
    frappe.log_error("Low Stock Automated Message", "running check_branch_low_stock triggered")

    try:
        # Email recipients per region
        RECIPIENTS = {
            "South America - VFL": ["merving@victoryfarmskenya.com"],
            # "South America - VFL": ["christinek@victoryfarmskenya.com"],
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

        allowed_parents = [
                "South America - VFL",
                "Antarctica - VFL",
                "North America - VFL",
                "Europe - VFL",
                "Asia - VFL",
                "Africa - VFL",
                "Victory Fresh - VFL"
        ]

        try:
            branches = frappe.get_all(
                "Warehouse",
                filters={
                    "warehouse_type": "Branch",
                    "parent_warehouse": ["in", allowed_parents]
                },
                fields=["name", "parent_warehouse"]
            )
        except Exception:
            return
    
        all_branch_messages = []
        all_email_recipients = set(ALWAYS_RECIPIENTS)
        all_sms_recipients = set(SMS_ALWAYS_RECIPIENTS)

        branch_index = 1

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

                        if 0 < qty <= MIN_STOCK_THRESHOLD:
                            low_stock_items.append(f"{item_code} (Qty: {qty})")
                        else:
                            continue
                    except Exception:
                        return
                        # frappe.log_error(
                        #     frappe.get_traceback(),
                        #     f"Stock fetch failed for Item: {item_code} in Branch: {branch_name}"
                        # )

                if low_stock_items:
                    items_str = ", ".join(low_stock_items)
                    branch_message = f"{branch_name} #{branch_index} is short on: {items_str}"
                    all_branch_messages.append(branch_message)
                    branch_index += 1

                    all_email_recipients.update(RECIPIENTS.get(parent_warehouse, []))
                    if SMS_RECIPIENTS.get(parent_warehouse):
                        all_sms_recipients.add(SMS_RECIPIENTS[parent_warehouse])

            except Exception:
                return
        if all_branch_messages:
            try:
                subject = "⚠️ Low Stock Alert: Nairobi Region Branches"

                email_message = (
                    f"Hello,<br><br>"
                    f"Be informed that the following branches are below the minimum stock size of 50kgs for different sizes:<br><br>"
                    + "<hr>".join(all_branch_messages)
                    + "<br><br>Please ensure the branches submit an order for stock up from VLC as soon as possible."
                )
                frappe.sendmail(
                    recipients=list(all_email_recipients),
                    bcc="christinek@victoryfarmskenya.com",
                    subject=subject,
                    message=email_message,
                    now=True
                )
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    "Failed to send low stock summary email"
                )

            try:
                sms_message = (
                    "Hello, Be informed that the following branches are below the minimum stock size of 50kgs for different sizes:\n\n"
                    + "\n".join(all_branch_messages)
                    + "\n\nPlease ensure the branches submit an order for stock up from VLC as soon as possible."
                )

                for mobile_no in all_sms_recipients:
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
                            f"Failed to send SMS to {mobile_no}"
                        )
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    "SMS preparation failed"
                )

        else:
            frappe.log_error("No branches had low stock. No email or SMS sent.", "Low Stock Check")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Unexpected error in check_branch_low_stock")
