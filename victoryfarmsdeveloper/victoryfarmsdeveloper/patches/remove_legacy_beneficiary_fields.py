import frappe


def execute():
    """Remove legacy single beneficiary custom fields from Payment Entry.

    These fields were replaced by the `custom_beneficiaries` child table
    (Payment Entry Beneficiary) and are no longer needed.
    """
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
        try:
            if frappe.db.exists("Custom Field", field_name):
                frappe.delete_doc("Custom Field", field_name, force=1)
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Failed to delete {field_name}: {str(e)}")

    # Ensure the new child table field exists and is configured correctly.
    _ensure_beneficiary_child_table()


def _ensure_beneficiary_child_table():
    """Create or update the custom_beneficiaries child table field."""
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
