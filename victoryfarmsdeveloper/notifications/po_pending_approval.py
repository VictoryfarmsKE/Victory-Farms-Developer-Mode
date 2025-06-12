import frappe

def send_pending_po_notifications(batch_size=20):
    try:
        pending_pos = frappe.get_all(
            "Purchase Order",
            filters={"workflow_state": ["not in", ["Draft", "Approved", "To Amend", "Cancelled"]]},
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