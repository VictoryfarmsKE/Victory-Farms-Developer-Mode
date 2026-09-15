import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "VictoryFarmsDeveloper"
DOCTYPE = "Stock Entry"
SETTER = "Stock Entry-main-field_order"
ANCHOR = "custom_secondary_drivers_name"
SHOW_IF = "eval:doc.custom_weighbridge_tare_ref || doc.custom_weighbridge_gross_ref"

FIELDS = [
    {
        "fieldname": "custom_weighbridge_section",
        "fieldtype": "Section Break",
        "label": "Weighbridge",
        "collapsible": 0,
        "depends_on": SHOW_IF,
        "insert_after": ANCHOR,
        "module": MODULE,
    },
    {
        "fieldname": "custom_weighbridge_tare_ref",
        "fieldtype": "Link",
        "label": "Empty Weight Reading",
        "options": "Weighbridge Reading",
        "read_only": 1,
        "insert_after": "custom_weighbridge_section",
        "module": MODULE,
    },
    {
        "fieldname": "custom_weighbridge_gross_ref",
        "fieldtype": "Link",
        "label": "Loaded Weight Reading",
        "options": "Weighbridge Reading",
        "read_only": 1,
        "insert_after": "custom_weighbridge_tare_ref",
        "module": MODULE,
    },
    {
        "fieldname": "custom_weighbridge_column",
        "fieldtype": "Column Break",
        "insert_after": "custom_weighbridge_gross_ref",
        "module": MODULE,
    },
    {
        "fieldname": "custom_weighbridge_expected_kg",
        "fieldtype": "Float",
        "label": "Expected Load (Kg)",
        "precision": "3",
        "read_only": 1,
        "insert_after": "custom_weighbridge_column",
        "module": MODULE,
    },
    {
        "fieldname": "custom_weighbridge_actual_kg",
        "fieldtype": "Float",
        "label": "Actual Load (Kg)",
        "precision": "3",
        "read_only": 1,
        "insert_after": "custom_weighbridge_expected_kg",
        "module": MODULE,
    },
    {
        "fieldname": "custom_weighbridge_column_2",
        "fieldtype": "Column Break",
        "insert_after": "custom_weighbridge_actual_kg",
        "module": MODULE,
    },
    {
        "fieldname": "custom_weighbridge_variance_kg",
        "fieldtype": "Float",
        "label": "Variance (Kg)",
        "precision": "3",
        "read_only": 1,
        "insert_after": "custom_weighbridge_column_2",
        "module": MODULE,
    },
    {
        "fieldname": "custom_weighbridge_variance_pct",
        "fieldtype": "Float",
        "label": "Variance (%)",
        "precision": "2",
        "read_only": 1,
        "insert_after": "custom_weighbridge_variance_kg",
        "module": MODULE,
    },
]

ORDERED = [f["fieldname"] for f in FIELDS]


def enforce():
    if not frappe.db.exists("DocType", "Weighbridge Reading"):
        return

    create_custom_fields({DOCTYPE: FIELDS}, ignore_validate=True)

    for field in FIELDS:
        name = frappe.db.get_value(
            "Custom Field", {"dt": DOCTYPE, "fieldname": field["fieldname"]}, "name"
        )
        if name:
            frappe.db.set_value(
                "Custom Field",
                name,
                {
                    "insert_after": field["insert_after"],
                    "module": MODULE,
                    "depends_on": field.get("depends_on") or "",
                    "no_copy": 1,
                    "print_hide": 1,
                },
                update_modified=False,
            )

    reposition()

    frappe.db.commit()
    frappe.clear_cache(doctype=DOCTYPE)


def reposition():
    value = frappe.db.get_value("Property Setter", SETTER, "value")
    if not value:
        return

    try:
        order = json.loads(value)
    except ValueError:
        return

    if not isinstance(order, list) or ANCHOR not in order:
        return

    kept = [f for f in order if f and f not in ORDERED]

    if ANCHOR not in kept:
        return

    at = kept.index(ANCHOR) + 1
    rebuilt = kept[:at] + ORDERED + kept[at:]

    if rebuilt == order:
        return

    frappe.db.set_value(
        "Property Setter", SETTER, "value", json.dumps(rebuilt), update_modified=False
    )
    print("VictoryFarmsDeveloper: placed the Weighbridge section after {0}".format(ANCHOR))
