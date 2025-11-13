import frappe
from frappe.utils import add_days, today, getdate, nowdate

def send_pending_po_notifications(batch_size=10):
    try:
        pending_pos = frappe.get_all(
            "Purchase Order",
            filters={"workflow_state": ["not in", ["Draft", "Frozen", "Approved", "To Amend", "Cancelled"]]},
            fields=["name", "workflow_state"]
        )
        total = len(pending_pos)
        for batch_start in range(0, total, batch_size):
            batch = pending_pos[batch_start:batch_start+batch_size]
            for po in batch:
                doc = frappe.get_doc("Purchase Order", po.name)
                # Get the workflow for Purchase Order
                workflow = frappe.get_doc("Workflow", {"name": "PO With parallel appproval"})
                for state in workflow.states:
                    if state.state == doc.workflow_state:
                        role = state.allow_edit
                        # Get users with the role, but exclude those who are System Managers
                        users = frappe.get_all(
                            "Has Role",
                            filters={"role": role, "parenttype": "User"},
                            fields=["parent"]
                        )
                        filtered_users = []
                        for u in users:
                            # Exclude users who have the "System Manager" role
                            has_sys_mgr = frappe.db.exists(
                                "Has Role",
                                {"role": "System Manager", "parent": u.parent, "parenttype": "User"}
                            )
                            if not has_sys_mgr and frappe.db.get_value("User", u.parent, "enabled") == 1:
                                first_name = frappe.db.get_value("User", u.parent, "first_name")
                                filtered_users.append({"user": u.parent, "first_name": first_name})
                        for user_info in filtered_users:
                            try:
                                url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
                                frappe.sendmail(
                                    recipients=[user_info["user"]],
                                    subject="Daily summary: Purchase Order(s) Pending Approval",
                                    message = f"Hello {user_info['first_name']},<br><br>Purchase Order <b><a href=\"{url}\">{doc.name}</a></b> is pending your approval.<br>",
                                    now=True
                                )
                            except Exception as e:
                                frappe.log_error(f"Email error for {user_info['user']}: {e}", "PO Notification Debug")
    except Exception as e:
        frappe.log_error(f"General error: {e}", "PO Notification Debug")
        
def send_po_approved_notification(doc, method):
    try:
        #Get previous workflow state
        previous_doc = doc.get_doc_before_save()
        previous_state = previous_doc.workflow_state if previous_doc else None
        
        # Only send if transitioning to Approved
        if previous_state != "Approved" and doc.workflow_state == "Approved":
            #Fetch recipient emails
            owner_email = frappe.db.get_value("User", doc.owner, "email")
            supplier_email = frappe.db.get_value("Supplier", doc.supplier, "email_id")

            # if not owner_email or not supplier_email:
            #     frappe.log_error(
            #         title="PO Approved Email Notification",
            #         message=f"Missing email(s) for PO {doc.name}. Owner: {owner_email}, Supplier: {supplier_email}"
            #     )
            #     return
            # else:
                #Compose and send email
            try:
                pdf_attachment = frappe.attach_print(
                    doctype=doc.doctype,
                    name=doc.name,
                    file_name=f"{doc.name}",
                    print_format="Purchase Order VF",
                    print_letterhead=True
                )
                frappe.sendmail(
                    recipients=[supplier_email, owner_email],
                    # cc =[owner_email],
                    expose_recipients="header",
                    now=True,
                    subject=f"Purchase Order {doc.name} from Victory Farms Limited for {doc.supplier}",
                    message=(
                        f"Hello,<br><br>Please find attached a Purchase Order <b>{doc.name} for {doc.grand_total}{doc.currency}</b>.<br>"
                        f"<br>The delivery due date, address and instructions are included in the Purchase Order.<br>"
                        f"<br>If you have any questions, please let us know. Thank you</a>.<br>"
                        f"<br>Best Regards,<br>Victory Farms Limited<br>"
                    ),
                    attachments=[pdf_attachment]
                    
                )
            except Exception as e:
                    frappe.log_error(
                        title="PO Approved Email Notification",
                        message=f"Email sending failed for PO {doc.name}: {e}"
                    )
        else:
            return
    except Exception as e:
        # return
        frappe.log_error(
            title="PO Approved Email Notification",
            message=f"Fatal error in notification handler for PO {doc.name}: {e}"
        )

# POs > 90 days (with status draft, pending approval, to amend, to receive) to notify the PO owner to action the PO  
def notify_old_pos():
    try:
        cutoff_date = add_days(getdate(nowdate()), -90)
        old_pos = frappe.get_all(
            "Purchase Order",
            filters={
                "workflow_state": ["not in", ["Approved", "Cancelled", "Frozen"]],
                "creation": ["<=", cutoff_date]
            },
            fields=["name", "owner", "modified", "creation"]
        )
        #log old_pos (number)
        frappe.log_error(f"Found {len(old_pos)} old Purchase Orders")
        for po in old_pos:
            owner_email = frappe.db.get_value("User", po.owner, "email")
            #log list of owners
            # frappe.log_error(f"Notifying owner {owner_email} for PO {po.name}")
            if owner_email:
                try:
                    url = frappe.utils.get_url_to_form("Purchase Order", po.name)
                    frappe.sendmail(
                        recipients=[owner_email],
                        subject="Reminder: Action Required on Old Purchase Order",
                        message = f"Hello,<br><br>This is a reminder that Purchase Order <b><a href=\"{url}\">{po.name}</a></b> has been pending action since {po.modified}.<br>Please review and take the necessary steps to process this PO.<br>",
                        now=True
                    )
                except Exception as e:
                    frappe.log_error(f"Email error for {owner_email}: {e}", "Old PO Notification Debug")
    except Exception as e:
        frappe.log_error(f"General error: {e}", "Old PO Notification Debug")
        
# Automatically move documents from Draft/Amend to Frozen aged by 7 days old
def auto_freeze_old_pos():
    try:
        cutoff_date = add_days(getdate(nowdate()), -7)
        pos_to_freeze = frappe.get_all(
            "Purchase Order",
            filters={
                "workflow_state": ["in", ["Draft", "To Amend"]],
                "modified": ["<=", cutoff_date]
            },
            fields=["name"]
        )
        for po in pos_to_freeze:
            doc = frappe.get_doc("Purchase Order", po.name)
            doc.workflow_state = "Frozen"
            doc.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Auto-freeze error: {e}", "PO Auto-Freeze Debug")