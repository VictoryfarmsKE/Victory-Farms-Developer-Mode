import frappe

TARGET_FIELD = "taxes_and_charges"
TARGET_VALUE = 'eval:doc.custom_type=="Feeds"'


def execute():
    """
    Make Landed Costs non-mandatory on Purchase Receipt under all conditions and
    make the Purchase Taxes and Charges Template the only field driven by the
    Feeds rule.

    This supersedes update_purchase_receipt_mandatory_rules, whose cleanup only
    matched double-quoted rule values and therefore left behind single-quoted
    variants such as eval:doc.custom_type=='Feeds'.

    Also clears any hidden/depends_on rule hiding the Purchase Taxes and Charges
    Template so the Feeds mandatory rule is visible and enforceable.
    """
    _clear_stale_mandatory_rules()
    _clear_landed_cost_reqd()
    _ensure_taxes_template_visible()
    _apply_rule_to_taxes_template()

    frappe.clear_cache(doctype="Purchase Receipt")


def _clear_stale_mandatory_rules():
    stale = frappe.get_all(
        "Property Setter",
        filters={
            "doctype_or_field": "DocField",
            "doc_type": "Purchase Receipt",
            "property": "mandatory_depends_on",
        },
        fields=["name", "field_name", "value"],
    )

    for row in stale:
        if row.field_name == TARGET_FIELD:
            continue
        if "custom_type" not in (row.value or ""):
            continue
        frappe.delete_doc("Property Setter", row.name, force=1, ignore_permissions=True)


def _clear_landed_cost_reqd():
    """Delete every reqd / mandatory_depends_on setter on Purchase Receipt -> Landed Costs."""
    reqd_setters = frappe.get_all(
        "Property Setter",
        filters={
            "doctype_or_field": "DocField",
            "doc_type": "Purchase Receipt",
            "field_name": "landed_cost_voucher",
            "property": ["in", ["reqd", "mandatory_depends_on"]],
        },
        pluck="name",
    )

    for name in reqd_setters:
        frappe.delete_doc("Property Setter", name, force=1, ignore_permissions=True)


def _ensure_taxes_template_visible():
    """Remove hidden/depends_on setters that hide the Purchase Taxes and Charges Template."""
    stale = frappe.get_all(
        "Property Setter",
        filters={
            "doctype_or_field": "DocField",
            "doc_type": "Purchase Receipt",
            "field_name": TARGET_FIELD,
            "property": ["in", ["hidden", "depends_on"]],
        },
        fields=["name", "property", "value"],
    )

    for row in stale:
        if row.property == "hidden" or (
            row.property == "depends_on" and "custom_type" in (row.value or "")
        ):
            frappe.delete_doc("Property Setter", row.name, force=1, ignore_permissions=True)


def _apply_rule_to_taxes_template():
    filters = {
        "doctype_or_field": "DocField",
        "doc_type": "Purchase Receipt",
        "field_name": TARGET_FIELD,
        "property": "mandatory_depends_on",
    }

    existing = frappe.db.get_value("Property Setter", filters, "name")
    if existing:
        frappe.db.set_value("Property Setter", existing, "value", TARGET_VALUE)
        return

    ps = frappe.new_doc("Property Setter")
    ps.doctype_or_field = "DocField"
    ps.doc_type = "Purchase Receipt"
    ps.field_name = TARGET_FIELD
    ps.property = "mandatory_depends_on"
    ps.value = TARGET_VALUE
    ps.property_type = "Text"
    ps.module = "VictoryFarmsDeveloper"
    ps.insert(ignore_permissions=True)
