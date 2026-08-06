import frappe


def execute():
    """Clean up Payment Entry beneficiary layout.

    Removes legacy single beneficiary custom fields and ensures the new
    custom_beneficiaries child table field is present and configured.
    """
    _remove_legacy_fields()
    _ensure_beneficiary_child_table()


def _remove_legacy_fields():
    old_fields = [
        "Payment Entry-custom_beneficiary_name",
        "Payment Entry-custom_beneficiary_mobile_number",
        "Payment Entry-custom_beneficiary_document_type",
        "Payment Entry-custom_beneficiary_column_break",
        "Payment Entry-custom_beneficiary_document_number",
        "Payment Entry-custom_beneficiary_amount",
        "Payment Entry-custom_beneficiary_purpose_of_payment",
    ]

    for field_name in old_fields:
        if frappe.db.exists("Custom Field", field_name):
            frappe.delete_doc("Custom Field", field_name, force=1)
            frappe.db.commit()


def _ensure_beneficiary_child_table():
    field_name = "Payment Entry-custom_beneficiaries"

    if frappe.db.exists("Custom Field", field_name):
        cf = frappe.get_doc("Custom Field", field_name)
    else:
        cf = frappe.new_doc("Custom Field")
        cf.name = field_name
        cf.dt = "Payment Entry"
        cf.fieldname = "custom_beneficiaries"

    cf.fieldtype = "Table"
    cf.label = "Beneficiaries"
    cf.options = "Payment Entry Beneficiary"
    cf.insert_after = "custom_beneficiary_section"
    cf.module = "VictoryFarmsDeveloper"
    cf.save()
    frappe.db.commit()
