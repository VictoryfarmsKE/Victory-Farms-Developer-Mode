import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "VictoryFarmsDeveloper"
DIMENSION = "Processing Line"
FIELDNAME = "processing_line"
TO_FIELDNAME = "to_processing_line"
LINE_TYPES = ("Harvesting of Fish", "Fish Processing SUVAC")

CUSTOM_FIELDS = {
    "Stock Ledger Entry": [
        {
            "fieldname": FIELDNAME,
            "label": DIMENSION,
            "fieldtype": "Link",
            "options": DIMENSION,
            "insert_after": "vf_crate_no",
            "read_only": 1,
            "search_index": 0,
            "module": MODULE,
        },
    ],
    "Stock Entry Detail": [
        {
            "fieldname": FIELDNAME,
            "label": "Source " + DIMENSION,
            "fieldtype": "Link",
            "options": DIMENSION,
            "insert_after": "custom_line",
            "hidden": 1,
            "read_only": 1,
            "search_index": 0,
            "module": MODULE,
        },
        {
            "fieldname": TO_FIELDNAME,
            "label": "Target " + DIMENSION,
            "fieldtype": "Link",
            "options": DIMENSION,
            "insert_after": FIELDNAME,
            "hidden": 1,
            "read_only": 1,
            "search_index": 0,
            "module": MODULE,
        },
    ],
}


def enforce():
    if not frappe.db.exists("DocType", DIMENSION):
        return

    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    ensure_dimension()
    frappe.db.commit()

    for doctype in CUSTOM_FIELDS:
        frappe.clear_cache(doctype=doctype)


def ensure_dimension():
    if frappe.db.exists("Inventory Dimension", DIMENSION):
        return

    doc = frappe.new_doc("Inventory Dimension")
    doc.update(
        {
            "name": DIMENSION,
            "dimension_name": DIMENSION,
            "reference_document": DIMENSION,
            "apply_to_all_doctypes": 0,
            "document_type": "Stock Entry Detail",
            "istable": 1,
            "type_of_transaction": "Both",
            "source_fieldname": FIELDNAME,
            "target_fieldname": FIELDNAME,
        }
    )
    doc.db_insert()
    print("VictoryFarmsDeveloper: created Inventory Dimension {0}".format(DIMENSION))


def backfill():
    rows = frappe.db.sql(
        """
        select sed.name, sed.custom_line, sed.s_warehouse, sed.t_warehouse
        from `tabStock Entry` se
        join `tabStock Entry Detail` sed on sed.parent = se.name
        where se.stock_entry_type in %(types)s
            and se.docstatus = 1
            and sed.custom_line > 0
        """,
        {"types": LINE_TYPES},
        as_dict=True,
    )

    for row in rows:
        line = get_line(row.custom_line)
        frappe.db.set_value(
            "Stock Entry Detail",
            row.name,
            {
                FIELDNAME: line if row.s_warehouse else None,
                TO_FIELDNAME: line if row.t_warehouse else None,
            },
            update_modified=False,
        )
        frappe.db.sql(
            """
            update `tabStock Ledger Entry`
            set processing_line = %(line)s
            where voucher_type = 'Stock Entry' and voucher_detail_no = %(row)s
            """,
            {"line": line, "row": row.name},
        )

    if rows:
        print("VictoryFarmsDeveloper: set Processing Line on {0} stock entry row(s)".format(len(rows)))


def get_line(number):
    number = int(number)
    name = str(number)
    if not frappe.db.exists(DIMENSION, name):
        frappe.get_doc({"doctype": DIMENSION, "line_no": number}).insert(ignore_permissions=True)
    return name
