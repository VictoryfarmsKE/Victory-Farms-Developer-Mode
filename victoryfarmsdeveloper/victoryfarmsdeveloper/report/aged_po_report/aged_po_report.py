# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    # Pagination parameters
    page = int(filters.get("page", 1))
    page_length = int(filters.get("page_length", 50))
    offset = (page - 1) * page_length

    sql = f"""
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
            AND po.status != 'Completed'
            AND po.workflow_state LIKE 'Pending Approval%%'
            AND DATEDIFF(NOW(), po.creation) >= 10
        ORDER BY
            po.creation DESC
        LIMIT {page_length} OFFSET {offset}
    """

    data = frappe.db.sql(sql, filters, as_dict=True)

    # Get the active workflow for Purchase Order (cached)
    workflow_name = frappe.get_value("Workflow", {"document_type": "Purchase Order", "is_active": 1}, "name")
    workflow_doc = frappe.get_cached_doc("Workflow", workflow_name) if workflow_name else None

    # Cache user info to minimize DB hits
    user_cache = {}

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
                        user_id = u["parent"]
                        if user_id not in user_cache:
                            has_sys_mgr = frappe.db.exists(
                                "Has Role",
                                {"role": "System Manager", "parent": user_id, "parenttype": "User"}
                            )
                            enabled = frappe.db.get_value("User", user_id, "enabled")
                            full_name = frappe.db.get_value("User", user_id, "full_name")
                            user_cache[user_id] = (has_sys_mgr, enabled, full_name)
                        else:
                            has_sys_mgr, enabled, full_name = user_cache[user_id]
                        if not has_sys_mgr and enabled == 1:
                            filtered_users.append(full_name)
                    row["users_with_role"] = ", ".join([u["parent"] for u in users])
                    row["users_first_names"] = ", ".join(filtered_users)
                    break

    columns = [
        {"label": "Purchase Order #", "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 150},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 220},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 180},
        {"label": "Pending Approver", "fieldname": "users_first_names", "fieldtype": "Data", "width": 220},
        {"label": "Billed (%)", "fieldname": "per_billed", "fieldtype": "Percent", "width": 100},
        {"label": "Received (%)", "fieldname": "per_received", "fieldtype": "Percent", "width": 120},
        {"label": "Creation Date", "fieldname": "creation", "fieldtype": "Datetime", "width": 180},
        {"label": "Aging (Days)", "fieldname": "aging_days", "fieldtype": "Int", "width": 150},
    ]

    return columns, data