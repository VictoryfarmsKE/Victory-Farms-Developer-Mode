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
        fields=["name"],
    )

    data = []
    for pe in payment_entries:
        beneficiaries = frappe.get_all(
            "Payment Entry Beneficiary",
            filters={"parent": pe.name, "parenttype": "Payment Entry"},
            fields=[
                "mobile_number",
                "document_type",
                "document_number",
                "amount",
                "purpose_of_payment",
                "beneficiary_name",
            ],
        )
        for row in beneficiaries:
            data.append(
                {
                    "mobile_number": row.mobile_number,
                    "document_type": row.document_type,
                    "document_number": row.document_number,
                    "amount": row.amount,
                    "purpose_of_payment": row.purpose_of_payment,
                    "name": row.beneficiary_name,
                }
            )

    return data


@frappe.whitelist()
def download_mpesa_export():
    """Return report data for programmatic export if needed."""
    columns, data = execute()
    return {"columns": columns, "data": data}
