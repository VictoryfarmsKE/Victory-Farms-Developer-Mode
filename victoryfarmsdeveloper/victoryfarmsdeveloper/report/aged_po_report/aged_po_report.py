# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    sql = """
        SELECT
            po.name AS purchase_order,
            po.supplier,
            po.workflow_state,
            po.status,
            po.per_billed,
            po.per_received,
            po.creation,
            DATEDIFF(NOW(), po.creation) AS aging_days
        FROM
            `tabPurchase Order` po
        WHERE
            po.per_billed < 100
            AND po.per_received < 100
            AND DATEDIFF(NOW(), po.creation) >= 10
        ORDER BY
            po.creation DESC
    """

    data = frappe.db.sql(sql, filters, as_dict=True)

    # Get the active workflow for Purchase Order
    workflow_name = frappe.get_value("Workflow", {"document_type": "Purchase Order", "is_active": 1}, "name")
    workflow_doc = frappe.get_doc("Workflow", workflow_name) if workflow_name else None

    for row in data:
        row["workflow_role"] = ""
        row["users_with_role"] = ""
        row["users_first_names"] = ""
        if workflow_doc:
            for state in workflow_doc.states:
                if state.state == row["workflow_state"]:
                    role = state.allow_edit
                    row["workflow_role"] = role
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
                            full_name = frappe.db.get_value("User", u.parent, "full_name")
                            filtered_users.append(full_name)
                    row["users_with_role"] = ", ".join([u["parent"] for u in users])
                    row["users_first_names"] = ", ".join(filtered_users)
                    break

    columns = [
        {"label": "Purchase Order #", "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 150},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 220},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 180},
        # {"label": "Workflow Role", "fieldname": "workflow_role", "fieldtype": "Data", "width": 180},
        # {"label": "Users With Role", "fieldname": "users_with_role", "fieldtype": "Data", "width": 220},
        {"label": "Pending Approver", "fieldname": "users_first_names", "fieldtype": "Data", "width": 220},
        {"label": "Billed (%)", "fieldname": "per_billed", "fieldtype": "Percent", "width": 100},
        {"label": "Received (%)", "fieldname": "per_received", "fieldtype": "Percent", "width": 120},
        {"label": "Creation Date", "fieldname": "creation", "fieldtype": "Datetime", "width": 180},
        {"label": "Aging (Days)", "fieldname": "aging_days", "fieldtype": "Int", "width": 150},
    ]

    return columns, data