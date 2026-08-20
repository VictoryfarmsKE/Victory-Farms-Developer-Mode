import frappe

TARGET_FIELD = "taxes_and_charges"
TARGET_VALUE = 'eval:doc.custom_type=="Feeds"'
LANDED_COST_FIELDS = ("landed_cost_voucher", "custom_landed_costs")


def execute():
    """
    Make Landed Costs non-mandatory on Purchase Receipt under all conditions and
    make the Purchase Taxes and Charges Template the only field driven by the
    Feeds rule.

    Uses direct SQL for cleanup so that stale Property Setters are removed
    regardless of permission / document-event edge cases.
    """
    _clear_stale_feeds_rules()
    _clear_landed_cost_rules()
    _ensure_taxes_template_visible()
    _apply_rule_to_taxes_template()

    frappe.clear_cache(doctype="Purchase Receipt")


def _clear_stale_feeds_rules():
    """Remove any custom_type-based mandatory_depends_on rule except on taxes_and_charges."""
    frappe.db.sql(
        """
        DELETE FROM `tabProperty Setter`
        WHERE doctype_or_field = 'DocField'
          AND doc_type = 'Purchase Receipt'
          AND property = 'mandatory_depends_on'
          AND field_name != %s
          AND (
              value LIKE %s
              OR value LIKE %s
          )
        """,
        (TARGET_FIELD, "%custom_type==\"Feed\"%", "%custom_type==\"Feeds\"%"),
    )


def _clear_landed_cost_rules():
    """Delete reqd/mandatory_depends_on/hidden/depends_on setters on Landed Costs fields."""
    field_list = ", ".join("%s" for _ in LANDED_COST_FIELDS)

    # Remove reqd / mandatory_depends_on
    frappe.db.sql(
        f"""
        DELETE FROM `tabProperty Setter`
        WHERE doctype_or_field = 'DocField'
          AND doc_type = 'Purchase Receipt'
          AND field_name IN ({field_list})
          AND property IN ('reqd', 'mandatory_depends_on')
        """,
        LANDED_COST_FIELDS,
    )

    # Remove hidden and custom_type-based depends_on
    frappe.db.sql(
        f"""
        DELETE FROM `tabProperty Setter`
        WHERE doctype_or_field = 'DocField'
          AND doc_type = 'Purchase Receipt'
          AND field_name IN ({field_list})
          AND (
              property = 'hidden'
              OR (property = 'depends_on' AND value LIKE %s)
          )
        """,
        (*LANDED_COST_FIELDS, "%custom_type%"),
    )


def _ensure_taxes_template_visible():
    """Remove hidden/depends_on setters that hide the Purchase Taxes and Charges Template."""
    frappe.db.sql(
        """
        DELETE FROM `tabProperty Setter`
        WHERE doctype_or_field = 'DocField'
          AND doc_type = 'Purchase Receipt'
          AND field_name = %s
          AND (
              property = 'hidden'
              OR (property = 'depends_on' AND value LIKE %s)
          )
        """,
        (TARGET_FIELD, "%custom_type%"),
    )


def _apply_rule_to_taxes_template():
    """Ensure taxes_and_charges is mandatory only when custom_type == 'Feeds'."""
    existing = frappe.db.get_value(
        "Property Setter",
        {
            "doctype_or_field": "DocField",
            "doc_type": "Purchase Receipt",
            "field_name": TARGET_FIELD,
            "property": "mandatory_depends_on",
        },
        "name",
    )

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
