import frappe
from datetime import datetime
import json

@frappe.whitelist()
def check_low_stock():
    item_code = "Cement in 50KG bags"
    warehouse = "Consumables Store - VFL"
    
    # Get the current date & time
    now = datetime.now()
    posting_date = now.strftime("%Y-%m-%d")
    posting_time = now.strftime("%H:%M:%S")

    # Fetch stock balance using bin
    stock_qty = frappe.db.get_value("Bin", 
        {"item_code": item_code, "warehouse": warehouse},
        "actual_qty"
    ) or 0

    if stock_qty <= 300:
        # Notify users if stock is low
        recipients = [user.email for user in frappe.get_all("User", filters={"role": "Store Assistant"}, fields=["email"])]

        subject = "⚠️ Low Stock Alert: Cement in 50KG bags"
        message = f"Item Cement in 50KG bags stock is at {stock_qty} units in Consumables Store - VFL. Please restock!"
     
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
        RECIPIENTS = {
            "South America - VFL": ["merving@victoryfarmskenya.com"],
            "Antarctica - VFL": ["teresiak@victoryfarmskenya.com"],
            "North America - VFL": ["winniea@victoryfarmskenya.com"],
            "Europe - VFL": ["evans.otieno@victoryfarmskenya.com"],
            "Asia - VFL": ["jemutair@victoryfarmskenya.com"],
            "Africa - VFL": ["perezk@victoryfarmskenya.com"],
            "Victory Fresh - VFL": ["josephw@victoryfarmskenya.com"],
        }

        SMS_RECIPIENTS = {
            "South America - VFL": "+254704926558",
            "Antarctica - VFL": "+254799416393",
            "North America - VFL": "+254795959395",
            "Europe - VFL": "+254111996178",
            "Asia - VFL": "+254113789815",
            "Africa - VFL": "+254793453554",
            "Victory Fresh - VFL": "+254746760913"
        }

        BRANCH_CONTACTS = [
            {
                "branch_name": "Nairobi West - VFL",
                "sub_region": "Antarctica - VFL",
                "mobile_number": "+254743618774",
                "email_address": "nairobi_west-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Bombolulu - VFL",
                "sub_region": "Antarctica - VFL",
                "mobile_number": "+254700274615",
                "email_address": "bombolulu-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Satellite - VFL",
                "sub_region": "Antarctica - VFL",
                "mobile_number": "+254702104147",
                "email_address": "satellite-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Keroka - VFL",
                "sub_region": "Antarctica - VFL",
                "mobile_number": "+254701230621",
                "email_address": "kangemi2-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Kangemi - VFL",
                "sub_region": "Antarctica - VFL",
                "mobile_number": "+254702496019",
                "email_address": "kangemi-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Buruburu - VFL",
                "sub_region": "Antarctica - VFL",
                "mobile_number": "+254112002598",
                "email_address": "buruburu@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Antarctica - VFL",
                "mobile_number": "+254114889003",
                "email_address": "mathare-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Kawangware - VFL",
                "sub_region": "South America - VFL",
                "mobile_number": "+254720220923",
                "email_address": "kawangware-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Corner - VFL",
                "sub_region": "South America - VFL",
                "mobile_number": "+254700389936",
                "email_address": "dagoretti.kona@victoryfarmskenya.com"
            },
            {
                "branch_name": "Yaya - VFL",
                "sub_region": "South America - VFL",
                "mobile_number": "+254115547462",
                "email_address": "yaya@victoryfarmskenya.com"
            },
            {
                "branch_name": "Road - VFL",
                "sub_region": "South America - VFL",
                "mobile_number": "+254112272043",
                "email_address": "jogooroad-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "South - VFL",
                "sub_region": "South America - VFL",
                "mobile_number": "+254114608110",
                "email_address": "ksouth-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Huruma - VFL",
                "sub_region": "South America - VFL",
                "mobile_number": "+254112389514",
                "email_address": "huruma-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "South America - VFL",
                "mobile_number": "+254700416490",
                "email_address": "githurai-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "west Branch - VFL",
                "sub_region": "Europe - VFL",
                "mobile_number": "+254700850919",
                "email_address": "kahawawendani.branch@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Europe - VFL",
                "mobile_number": "+254702132180",
                "email_address": "thika.branch@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Europe - VFL",
                "mobile_number": "+254112207283",
                "email_address": "mwiki.branch@victoryfarmskenya.com"
            },
            {
                "branch_name": "Wendani Branch - VFL",
                "sub_region": "Europe - VFL",
                "mobile_number": "+254700839122",
                "email_address": "kahawawendani.branch@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Europe - VFL",
                "mobile_number": "+254700836279",
                "email_address": "jujabranch@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Europe - VFL",
                "mobile_number": "+254702652565",
                "email_address": "kasarani-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Europe - VFL",
                "mobile_number": "+254797774711",
                "email_address": "zimmerman-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Africa - VFL",
                "mobile_number": "+254701347623",
                "email_address": "mlolongo-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Africa - VFL",
                "mobile_number": "+254701386071",
                "email_address": "kitengela-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Africa - VFL",
                "mobile_number": "+254114823219",
                "email_address": "machakos-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Branch - VFL",
                "sub_region": "Africa - VFL",
                "mobile_number": "+254795340583",
                "email_address": "pipeline-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Daima Branch - VFL",
                "sub_region": "Africa - VFL",
                "mobile_number": "+254700421860",
                "email_address": "imara.daima@victoryfarmskenya.com"
            },
            {
                "branch_name": "Kayole Branch - VFL",
                "sub_region": "North America - VFL",
                "mobile_number": "+254705257018",
                "email_address": "Kayole-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Donholm Branch - VFL",
                "sub_region": "North America - VFL",
                "mobile_number": "+254112208097",
                "email_address": "Donholm-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Ruai Branch - VFL",
                "sub_region": "North America - VFL",
                "mobile_number": "+254797342420",
                "email_address": "Ruai-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Umoja Branch - VFL",
                "sub_region": "North America - VFL",
                "mobile_number": "+254702141137",
                "email_address": "umoja-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Utawala - VFL",
                "sub_region": "North America - VFL",
                "mobile_number": "+254797774280",
                "email_address": "utawala-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Kangundo Road Branch - VFL",
                "sub_region": "North America - VFL",
                "mobile_number": "+254700888773",
                "email_address": "Kangundoroad.branch@victoryfarmskenya.com"
            },
            {
                "branch_name": "Dandora - VFL",
                "sub_region": "North America - VFL",
                "mobile_number": "+254701560824",
                "email_address": "Dandora-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Ngara - VFL",
                "sub_region": "Asia - VFL",
                "mobile_number": "+254115546469",
                "email_address": "ngara-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Ngong - VFL",
                "sub_region": "Asia - VFL",
                "mobile_number": "+254701909656",
                "email_address": "ngong-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Ongata Rongai - VFL",
                "sub_region": "Asia - VFL",
                "mobile_number": "+254746717744",
                "email_address": "ongatarongai-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Garden Estate - VFL",
                "sub_region": "Asia - VFL",
                "mobile_number": "+254700412918",
                "email_address": "garden.city@victoryfarmskenya.com"
            },
            {
                "branch_name": "Lucky Summer - VFL",
                "sub_region": "Asia - VFL",
                "mobile_number": "+254701410386",
                "email_address": "luckysummer-sales@victoryfarmskenya.com"
            },
            {
                "branch_name": "Kariobangi North - VFL",
                "sub_region": "Asia - VFL",
                "mobile_number": "+254701395369",
                "email_address": "kariobangi.north@victoryfarmskenya.com"
            }
        ]

        ALWAYS_RECIPIENTS = [
            "cynthiar@victoryfarmskenya.com",
            "stephennj@victoryfarmskenya.com"
            # "christinek@victoryfarmskenya.com"
        ]

        SMS_ALWAYS_RECIPIENTS = [
            # "+254113574233",
            # "+254711810457"
            # "+254710899291"
        ]

        ITEM_CODES = ["Large Size", "Medium Size", "Small Size"]
        MIN_STOCK_THRESHOLD = 50

        now = datetime.now()
        posting_date = now.strftime("%Y-%m-%d")
        posting_time = now.strftime("%H:%M:%S")

        allowed_parents = list(RECIPIENTS.keys())

        branches = frappe.get_all(
            "Warehouse",
            filters={
                "warehouse_type": "Branch",
                "parent_warehouse": ["in", allowed_parents]
            },
            fields=["name", "parent_warehouse"]
        )

        all_branch_messages = []
        all_email_recipients = set(ALWAYS_RECIPIENTS)
        all_sms_recipients = set(SMS_ALWAYS_RECIPIENTS)
        branch_index = 1

        for branch in branches:
            branch_name = branch["name"]
            parent_warehouse = branch.get("parent_warehouse", "").strip()
            if parent_warehouse not in allowed_parents:
                continue

            low_stock_items = []
            for item_code in ITEM_CODES:
                try:
                    qty = frappe.db.get_value("Bin",
                        {"item_code": item_code, "warehouse": branch_name},
                        "actual_qty"
                    ) or 0
                    if 0 < qty <= MIN_STOCK_THRESHOLD:
                        low_stock_items.append(f"{item_code} (Qty: {qty})")
                except Exception:
                    continue

            if not low_stock_items:
                continue

            items_str = ", ".join(low_stock_items)
            branch_message = f"{branch_name} #{branch_index} is short on: {items_str}"
            all_branch_messages.append(branch_message)
            branch_index += 1

            # Add region contacts
            all_email_recipients.update(RECIPIENTS.get(parent_warehouse, []))
            if SMS_RECIPIENTS.get(parent_warehouse):
                all_sms_recipients.add(SMS_RECIPIENTS[parent_warehouse])

            # Send to individual branch contacts
            # contact = next((c for c in BRANCH_CONTACTS if c["branch_name"] == branch_name), None)
            # if contact:
                # try:
                #     # Email
                #     branch_email_msg = (
                #         f"Hello,<br><br>Be informed that {branch_name} is below the minimum stock size of 50kgs for different sizes<br><b>{items_str}</b><br><br>"
                #         "Please submit an order for stock up from VLC as soon as possible."
                #     )
                #     frappe.sendmail(
                #         recipients=[contact["email_address"]],
                #         subject=f"⚠️ Low Stock Alert - {branch_name}",
                #         message=branch_email_msg,
                #         now=True
                #     )

                #     # SMS
                #     sms_msg = (
                #         f"Be informed that {branch_name} is below the minimum stock size of 50kgs on: \n{items_str}. \n\nPlease submit an order for stock up from VLC as soon as possible.\n"
                #     )
                #     frappe.call(
                #         "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings.send_sms",
                #         receiver_list=json.dumps([contact["mobile_number"]]),
                #         msg=sms_msg
                #     )
                # except Exception:
                #     frappe.log_error(frappe.get_traceback(), f"Failed to notify {branch_name} contacts")

        # Send regional summary
        if all_branch_messages:
            try:
                subject = "⚠️ Low Stock Alert: Nairobi Region Branches"
                email_message = (
                    f"Hello,<br><br>"
                    f"Be informed that the following branches are below the minimum stock size of 50kgs for different sizes:<br>"
                    + "<hr>".join(all_branch_messages)
                    + "<br><br>Please ensure the branches submit an order for stock up from VLC as soon as possible."
                )
                frappe.sendmail(
                    recipients=list(all_email_recipients),
                    expose_recipients="header",
                    bcc="christinek@victoryfarmskenya.com",
                    subject=subject,
                    message=email_message,
                    now=True
                )
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Failed to send region summary email")

            # try:
            #     sms_message = (
            #         "Hello, Be informed that the following branches are below the minimum stock size of 50kgs for different sizes:\n\n" +
            #         "\n".join(all_branch_messages) +
            #         "\n\nPlease ensure the branches submit an order for stock up from VLC as soon as possible."
            #     )
            #     for mobile_no in all_sms_recipients:
            #         try:
            #             response = frappe.call(
            #                 "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings.send_sms",
            #                 receiver_list=json.dumps([mobile_no]),
            #                 msg=sms_message
            #             )
            #             if response:
            #                 try:
            #                     response_json = json.loads(response)
            #                     frappe.log_error(str(response_json), f"SMS Sent to {mobile_no}")
            #                 except json.JSONDecodeError:
            #                     pass
            #         except Exception:
            #             frappe.log_error(frappe.get_traceback(), f"Failed SMS to {mobile_no}")
            # except Exception:
            #     frappe.log_error(frappe.get_traceback(), "SMS summary failed")

        else:
            frappe.log_error("No branches with low stock. No email/SMS sent.", "Low Stock Summary")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Unexpected error in check_branch_low_stock")