import frappe


def execute():
    """
    Remove the Feeds-specific mandatory rule on Purchase Receipt's
    Landed Costs field and add the same rule to the Purchase Taxes and
    Charges table.
    """
    # Remove mandatory_depends_on from the landed_cost_voucher (Landed Costs) field
    frappe.db.delete(
        "Property Setter",
        {
            "doctype_or_field": "DocField",
            "doc_type": "Purchase Receipt",
            "field_name": "landed_cost_voucher",
            "property": "mandatory_depends_on",
        },
    )

    # Add mandatory_depends_on to the taxes (Purchase Taxes and Charges) table
    taxes_filters = {
        "doctype_or_field": "DocField",
        "doc_type": "Purchase Receipt",
        "field_name": "taxes",
        "property": "mandatory_depends_on",
    }

    existing_name = frappe.db.get_value("Property Setter", taxes_filters, "name")
    if existing_name:
        frappe.db.set_value(
            "Property Setter",
            existing_name,
            "value",
            'eval:doc.custom_type=="Feeds"',
        )
    else:
        ps = frappe.new_doc("Property Setter")
        ps.doctype_or_field = "DocField"
        ps.doc_type = "Purchase Receipt"
        ps.field_name = "taxes"
        ps.property = "mandatory_depends_on"
        ps.value = 'eval:doc.custom_type=="Feeds"'
        ps.property_type = "Text"
        ps.module = "VictoryFarmsDeveloper"
        ps.insert()

    frappe.clear_cache(doctype="Purchase Receipt")
