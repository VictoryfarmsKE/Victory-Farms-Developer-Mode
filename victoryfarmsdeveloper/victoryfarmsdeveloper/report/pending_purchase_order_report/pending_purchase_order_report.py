# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Purchase Order #"),
            "fieldname": "purchase_order",
            "fieldtype": "Link",
            "options": "Purchase Order",
            "width": 160,
        },
        {
            "label": _("Created By"),
            "fieldname": "created_by",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Creation Date"),
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 160,
        },
        {
            "label": _("Days Since Creation"),
            "fieldname": "aging_days",
            "fieldtype": "Int",
            "width": 180,
        },
        {
            "label": _("Approval Status"),
            "fieldname": "workflow_state",
            "fieldtype": "Data",
            "width": 220,
        },

        {
            "label": _("Supplier Name"),
            "fieldname": "supplier_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 180,
        },
        {
            "label": _("Cost Centre"),
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 200,
        },
        {
            "label": _("Requester"),
            "fieldname": "requester",
            "fieldtype": "Data",
            "width": 140,
        },


        {
            "label": _("Grand Total"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 140,
        },


    ]


def get_data(filters):
    current_user = frappe.session.user
    roles = set(frappe.get_roles(current_user))

    conditions = [
        "po.workflow_state LIKE %(pending_state)s"
    ]

    values = {
        "pending_state": "Pending%",
        "current_user": current_user,
    }
    page_length = int(filters.get("page_length") or 100)

    allowed_page_lengths = [50, 100, 250, 500]

    if page_length not in allowed_page_lengths:
        page_length = 100

    values["page_length"] = page_length

    # ---------------------------------------------------------
    # PERMISSION CONDITIONS
    # ---------------------------------------------------------

    permission_condition, permission_values = get_permission_condition(
        current_user,
        roles,
    )

    if permission_condition:
        conditions.append(permission_condition)

    values.update(permission_values)

    # ---------------------------------------------------------
    # USER-SELECTED REPORT FILTERS
    # ---------------------------------------------------------

    if filters.get("department"):
        conditions.append(
            "po.custom_department = %(department)s"
        )
        values["department"] = filters.department

    if filters.get("cost_center"):
        conditions.append(
            "po.cost_center = %(cost_center)s"
        )
        values["cost_center"] = filters.cost_center

    if filters.get("requester"):
        conditions.append(
            "po.custom_requested_by = %(requester)s"
        )
        values["requester"] = filters.requester

    if filters.get("created_by"):
        created_by = filters.get("created_by")

        if isinstance(created_by, str):
            created_by = [created_by]

        placeholders = []

        for idx, user in enumerate(created_by):
            key = f"created_by_{idx}"
            placeholders.append(f"%({key})s")
            values[key] = user

        conditions.append(
            f"po.owner IN ({', '.join(placeholders)})"
        )
    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            po.name AS purchase_order,
            po.creation,
            DATEDIFF(CURDATE(), DATE(po.creation)) AS aging_days,
            po.supplier_name,

            po.custom_department AS department,
            po.cost_center,

            COALESCE(requester.full_name, po.custom_requested_by, '') AS requester,
            COALESCE(creator.full_name, po.owner) AS created_by,

            po.workflow_state,
            po.grand_total

        FROM
            `tabPurchase Order` po

        LEFT JOIN
            `tabUser` creator
                ON creator.name = po.owner

        LEFT JOIN
            `tabUser` requester
                ON requester.name = po.custom_requested_by

        WHERE
            {where_clause}

            AND EXISTS (
                SELECT 1
                FROM `tabEmployee` procurement_employee
                WHERE procurement_employee.user_id = po.owner
                    AND procurement_employee.department = 'Procurement - VFL'
            )

        ORDER BY
            po.creation ASC
            LIMIT %(page_length)s
    """

    return frappe.db.sql(sql, values, as_dict=True)


def get_permission_condition(current_user, roles):
    """
    Determines which Purchase Orders the logged-in user
    is allowed to see in this report.

    Access:
        System Manager / Executive Manager:
            All pending Procurement-created POs.

        HOD / Finance Manager:
            POs belonging to the user's Employee department.

        Procurement Team / Procurement User - VF:
            Only POs created by the logged-in user.
    """

    # ---------------------------------------------------------
    # LEVEL 1: FULL ACCESS
    # ---------------------------------------------------------

    full_access_roles = {
        "System Manager",
        "Executive Manager",
    }

    if roles.intersection(full_access_roles):
        return "", {}

    # ---------------------------------------------------------
    # LEVEL 2: DEPARTMENT ACCESS
    # ---------------------------------------------------------

    department_access_roles = {
        "HOD",
        "Finance Manager",
    }

    if roles.intersection(department_access_roles):
        department = frappe.db.get_value(
            "Employee",
            {
                "user_id": current_user,
                "status": "Active",
            },
            "department",
        )

        if not department:
            # Fail closed.
            # If we cannot determine the employee's department,
            # don't expose records.
            return "1 = 0", {}

        return (
            "po.custom_department = %(user_department)s",
            {"user_department": department},
        )

    # ---------------------------------------------------------
    # LEVEL 3: OWN RECORDS ONLY
    # ---------------------------------------------------------

    return (
        "po.owner = %(current_user)s",
        {"current_user": current_user},
    )