import frappe

SOURCE_DOCTYPE = "Supplier"
FIELDNAME = "custom_localforeign"
LABEL = "Local/Import"
GROUP_FIELDNAME = "custom_supplier_group"
GATE_FIELD = "supplier"
GATE_PROPERTY = "depends_on"
TARGET_DOCTYPES = ("Purchase Order", "Purchase Invoice", "Purchase Receipt")
GATE_DOCTYPES = ("Purchase Order",)
FALLBACK_OPTIONS = "\nLocal\nImport\nForeign"
FALLBACK_INSERT_AFTER = "naming_series"
BATCH_SIZE = 500


def execute():
    options = _get_local_import_options()

    for doctype in TARGET_DOCTYPES:
        _ensure_field(doctype, options)

    for doctype in GATE_DOCTYPES:
        _ensure_supplier_gate(doctype)

    frappe.db.commit()

    for doctype in TARGET_DOCTYPES:
        frappe.clear_cache(doctype=doctype)

    for doctype in TARGET_DOCTYPES:
        _backfill(doctype)

    frappe.clear_cache()


def _get_local_import_options():
    options = frappe.db.get_value(
        "Custom Field", {"dt": SOURCE_DOCTYPE, "fieldname": FIELDNAME}, "options"
    )

    if not options:
        try:
            field = frappe.get_meta(SOURCE_DOCTYPE).get_field(FIELDNAME)
            options = field.options if field else None
        except Exception:
            options = None

    if not options:
        frappe.log_error(
            "Could not resolve {0}.{1} options; falling back to {2}".format(
                SOURCE_DOCTYPE, FIELDNAME, FALLBACK_OPTIONS.split("\n")
            ),
            "add_local_import_to_buying_docs",
        )
        return FALLBACK_OPTIONS

    return options


def _get_insert_after(doctype):
    if frappe.db.exists("Custom Field", "{0}-{1}".format(doctype, GROUP_FIELDNAME)):
        return GROUP_FIELDNAME

    return FALLBACK_INSERT_AFTER


def _ensure_field(doctype, options):
    name = "{0}-{1}".format(doctype, FIELDNAME)

    if frappe.db.exists("Custom Field", name):
        cf = frappe.get_doc("Custom Field", name)
    else:
        cf = frappe.new_doc("Custom Field")
        cf.name = name
        cf.dt = doctype
        cf.fieldname = FIELDNAME

    cf.label = LABEL
    cf.fieldtype = "Select"
    cf.options = options
    cf.insert_after = _get_insert_after(doctype)
    cf.fetch_from = None
    cf.fetch_if_empty = 0
    cf.read_only = 0
    cf.reqd = 0
    cf.allow_on_submit = 0
    cf.in_standard_filter = 1
    cf.module = "VictoryFarmsDeveloper"
    cf.save()


def _ensure_supplier_gate(doctype):
    existing = frappe.db.get_value(
        "Property Setter",
        {
            "doctype_or_field": "DocField",
            "doc_type": doctype,
            "field_name": GATE_FIELD,
            "property": GATE_PROPERTY,
        },
        ["name", "value"],
        as_dict=True,
    )

    clause = "doc.{0}".format(FIELDNAME)

    if existing:
        current = (existing.value or "").strip()

        if clause in current:
            return

        if not current:
            value = "eval:{0}".format(clause)
        elif current.startswith("eval:"):
            value = "{0} && {1}".format(current, clause)
        else:
            frappe.log_error(
                "Unexpected {0}.{1} {2} value {3!r}; leaving it untouched".format(
                    doctype, GATE_FIELD, GATE_PROPERTY, current
                ),
                "add_local_import_to_buying_docs",
            )
            return

        frappe.db.set_value("Property Setter", existing.name, "value", value)
        frappe.db.set_value(
            "Property Setter", existing.name, "module", "VictoryFarmsDeveloper"
        )
        return

    ps = frappe.new_doc("Property Setter")
    ps.doctype_or_field = "DocField"
    ps.doc_type = doctype
    ps.field_name = GATE_FIELD
    ps.property = GATE_PROPERTY
    ps.value = "eval:{0}".format(clause)
    ps.property_type = "Data"
    ps.module = "VictoryFarmsDeveloper"
    ps.insert(ignore_permissions=True)


def _backfill(doctype):
    rows = frappe.get_all(
        doctype,
        filters=[[FIELDNAME, "is", "not set"], [GATE_FIELD, "is", "set"]],
        fields=["name", GATE_FIELD],
    )

    if not rows:
        return

    suppliers = {row.get(GATE_FIELD) for row in rows}
    values = dict(
        frappe.get_all(
            SOURCE_DOCTYPE,
            filters=[["name", "in", list(suppliers)]],
            fields=["name", FIELDNAME],
            as_list=True,
        )
    )

    updated = 0

    for row in rows:
        value = values.get(row.get(GATE_FIELD))

        if not value:
            continue

        frappe.db.set_value(
            doctype, row.name, FIELDNAME, value, update_modified=False
        )
        updated += 1

        if updated % BATCH_SIZE == 0:
            frappe.db.commit()

    frappe.db.commit()

    print(
        "VictoryFarmsDeveloper: backfilled {0} on {1} {2} record(s)".format(
            FIELDNAME, updated, doctype
        )
    )
