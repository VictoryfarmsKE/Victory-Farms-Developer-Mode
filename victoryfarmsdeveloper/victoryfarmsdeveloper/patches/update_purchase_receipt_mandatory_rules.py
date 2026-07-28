import frappe

def execute():
    # Remove old mandatory_depends_on rules from taxes and landed_cost_voucher
    old_setters = frappe.get_all("Property Setter", filters={
        "doc_type": "Purchase Receipt",
        "property": "mandatory_depends_on",
        "field_name": ["in", ["taxes", "landed_cost_voucher"]]
    }, pluck="name")

    for ps_name in old_setters:
        frappe.delete_doc("Property Setter", ps_name, force=1)

    # Add mandatory_depends_on to taxes_and_charges when custom_type is "Feeds"
    if not frappe.db.exists("Property Setter", {
        "doc_type": "Purchase Receipt",
        "field_name": "taxes_and_charges",
        "property": "mandatory_depends_on"
    }):
        ps = frappe.new_doc("Property Setter")
        ps.doctype_or_field = "DocField"
        ps.doc_type = "Purchase Receipt"
        ps.field_name = "taxes_and_charges"
        ps.property = "mandatory_depends_on"
        ps.value = "eval:doc.custom_type=='Feeds'"
        ps.property_type = "Data"
        ps.insert(ignore_permissions=True)
    else:
        ps = frappe.get_doc("Property Setter", {
            "doc_type": "Purchase Receipt",
            "field_name": "taxes_and_charges",
            "property": "mandatory_depends_on"
        })
        ps.value = "eval:doc.custom_type=='Feeds'"
        ps.save()

    frappe.db.commit()
