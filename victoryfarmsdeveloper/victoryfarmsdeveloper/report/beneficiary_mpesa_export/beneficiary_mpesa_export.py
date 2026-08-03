import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"fieldname": "mobile_number", "label": "MobileNumber", "fieldtype": "Data", "width": 160},
        {"fieldname": "document_type", "label": "DocumentType", "fieldtype": "Data", "width": 140},
        {"fieldname": "document_number", "label": "DocumentNumber", "fieldtype": "Data", "width": 160},
        {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 140},
        {"fieldname": "purpose_of_payment", "label": "PurposeOfPayment", "fieldtype": "Data", "width": 200},
        {"fieldname": "name", "label": "Name", "fieldtype": "Data", "width": 200},
    ]


def get_data(filters):
    filters = filters or {}

    query_filters = {
        "docstatus": ["in", [0, 1]],
        "custom_beneficiary_name": ["is", "set"],
    }

    if filters.get("company"):
        query_filters["company"] = filters["company"]
    if filters.get("posting_date"):
        query_filters["posting_date"] = filters["posting_date"]
    if filters.get("from_date") and filters.get("to_date"):
        query_filters["posting_date"] = ["between", [filters["from_date"], filters["to_date"]]]

    payment_entries = frappe.get_all(
        "Payment Entry",
        filters=query_filters,
        fields=[
            "name",
            "custom_beneficiary_name",
            "custom_beneficiary_mobile_number",
            "custom_beneficiary_document_type",
            "custom_beneficiary_document_number",
            "custom_beneficiary_amount",
            "custom_beneficiary_purpose_of_payment",
        ],
    )

    data = []
    for pe in payment_entries:
        # Replace newline-separated PO refs with pipe separator for Excel export
        purpose = (pe.custom_beneficiary_purpose_of_payment or "").replace("\n", " | ")

        data.append(
            {
                "mobile_number": pe.custom_beneficiary_mobile_number,
                "document_type": pe.custom_beneficiary_document_type,
                "document_number": pe.custom_beneficiary_document_number,
                "amount": pe.custom_beneficiary_amount,
                "purpose_of_payment": purpose,
                "name": pe.custom_beneficiary_name,
            }
        )

    return data


@frappe.whitelist()
def download_mpesa_export():
    """Return report data for programmatic export if needed."""
    columns, data = execute()
    return {"columns": columns, "data": data}
