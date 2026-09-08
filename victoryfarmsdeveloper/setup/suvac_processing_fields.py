"""
SUVAC processing fields on Stock Entry Detail.

Wired to `after_migrate` rather than `patches.txt` for the same reason as
`purchase_receipt_field_rules`: other installed apps ship a `field_order` Property Setter
for Stock Entry Detail as a `sync_on_migrate` fixture. A `field_order` is the complete
ordered field list for a doctype, so every field missing from that snapshot stops rendering.
Upande's snapshot predates these fields and drops 20+ of them, including SUVAC's.

`sync_customizations` runs after all patches, so a patch cannot win. Only `after_migrate`
runs last, on every migrate.

`restore_hidden_fields` appends anything missing rather than replacing the list, so the
ordering other apps intend is preserved.
"""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "VictoryFarmsDeveloper"
DOCTYPE = "Stock Entry Detail"
LAYOUT_DOCTYPES = ("Stock Entry Detail", "Stock Entry")

CUSTOM_FIELDS = {
    DOCTYPE: [
        {
            "fieldname": "custom_line",
            "label": "Processing Line",
            "fieldtype": "Float",
            "insert_after": "fish_cage",
            "in_list_view": 1,
            "module": MODULE,
        },
        {
            "fieldname": "custom_dispatch_room",
            "label": "Dispatch Room",
            "fieldtype": "Link",
            "options": "Warehouse",
            "insert_after": "custom_line",
            "in_list_view": 1,
            "module": MODULE,
        },
    ]
}

STOCK_ENTRY_TYPE = {"name": "Fish Transfer From FLC To Dispatch", "purpose": "Material Transfer"}


def enforce():
    ensure_custom_fields()
    ensure_stock_entry_type()

    for doctype in LAYOUT_DOCTYPES:
        restore_hidden_fields(doctype)

    frappe.db.commit()

    for doctype in LAYOUT_DOCTYPES:
        frappe.clear_cache(doctype=doctype)


def ensure_custom_fields():
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)

    for field in CUSTOM_FIELDS[DOCTYPE]:
        name = frappe.db.get_value(
            "Custom Field", {"dt": DOCTYPE, "fieldname": field["fieldname"]}, "name"
        )
        if name:
            frappe.db.set_value("Custom Field", name, "module", MODULE, update_modified=False)


def ensure_stock_entry_type():
    if frappe.db.exists("Stock Entry Type", STOCK_ENTRY_TYPE["name"]):
        return

    doc = frappe.new_doc("Stock Entry Type")
    doc.name = STOCK_ENTRY_TYPE["name"]
    doc.purpose = STOCK_ENTRY_TYPE["purpose"]
    doc.insert(ignore_permissions=True)
    print("VictoryFarmsDeveloper: created Stock Entry Type {0}".format(STOCK_ENTRY_TYPE["name"]))


def restore_hidden_fields(doctype):
    setter = "{0}-main-field_order".format(doctype)
    value = frappe.db.get_value("Property Setter", setter, "value")
    if not value:
        return

    try:
        order = json.loads(value)
    except ValueError:
        return

    if not isinstance(order, list):
        return

    cleaned = [fieldname for fieldname in order if fieldname]
    dropped = len(order) - len(cleaned)
    order = cleaned

    anchors = {}
    missing = []
    for field in frappe.get_meta(doctype).fields:
        if not field.fieldname or field.fieldname in order:
            continue
        missing.append(field.fieldname)
        anchors[field.fieldname] = frappe.db.get_value(
            "Custom Field", {"dt": doctype, "fieldname": field.fieldname}, "insert_after"
        )

    if not missing and not dropped:
        return

    pending = list(missing)
    while pending:
        placed = []
        for fieldname in pending:
            anchor = anchors.get(fieldname)
            if anchor and anchor in order:
                order.insert(order.index(anchor) + 1, fieldname)
                placed.append(fieldname)

        if not placed:
            order.extend(pending)
            break

        for fieldname in placed:
            pending.remove(fieldname)

    frappe.db.set_value(
        "Property Setter",
        setter,
        "value",
        json.dumps(order),
        update_modified=False,
    )

    if dropped:
        print(
            "VictoryFarmsDeveloper: dropped {0} empty entry(s) from the {1} layout".format(
                dropped, doctype
            )
        )

    if missing:
        print(
            "VictoryFarmsDeveloper: restored {0} hidden field(s) on {1}: {2}".format(
                len(missing), doctype, ", ".join(missing)
            )
        )
