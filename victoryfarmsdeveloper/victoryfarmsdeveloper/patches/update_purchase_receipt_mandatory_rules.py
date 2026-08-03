import frappe


def execute():
    """
    Remove any Feed/Feeds-specific mandatory rule from any Purchase Receipt
    field except taxes_and_charges, and add the same rule to the Purchase
    Taxes and Charges Template field.
    """
    target_value = 'eval:doc.custom_type=="Feeds"'
    target_field = "taxes_and_charges"

    # Remove any Feed/Feeds-specific mandatory_depends_on from any Purchase Receipt
    # field other than taxes_and_charges. This cleans up the legacy rule on
    # landed_cost_voucher (Landed Costs), the taxes child table, or any other
    # field that might have inherited the rule.
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
        (target_field, "%custom_type==\"Feed\"%", "%custom_type==\"Feeds\"%"),
    )

    # Add mandatory_depends_on to the taxes_and_charges (Purchase Taxes and Charges Template) field
    template_filters = {
        "doctype_or_field": "DocField",
        "doc_type": "Purchase Receipt",
        "field_name": target_field,
        "property": "mandatory_depends_on",
    }

    existing_name = frappe.db.get_value("Property Setter", template_filters, "name")
    if existing_name:
        frappe.db.set_value(
            "Property Setter",
            existing_name,
            "value",
            target_value,
        )
    else:
        ps = frappe.new_doc("Property Setter")
        ps.doctype_or_field = "DocField"
        ps.doc_type = "Purchase Receipt"
        ps.field_name = target_field
        ps.property = "mandatory_depends_on"
        ps.value = target_value
        ps.property_type = "Text"
        ps.module = "VictoryFarmsDeveloper"
        ps.insert()

    frappe.clear_cache(doctype="Purchase Receipt")
