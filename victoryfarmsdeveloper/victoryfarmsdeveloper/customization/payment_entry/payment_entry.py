import frappe
from frappe import _


def set_beneficiary_purpose_of_payment(doc, method=None):
    """Auto-fill Beneficiary Purpose of Payment from Purchase Order references.

    Multiple POs are joined with newlines (one per line) so the rare case of
    one Payment Entry paying several POs is still clearly represented.
    """
    if not doc.references:
        return

    po_refs = [
        r.reference_name
        for r in doc.references
        if r.reference_doctype == "Purchase Order" and r.reference_name
    ]
    po_refs = list(dict.fromkeys(po_refs))  # preserve order, remove duplicates

    if not po_refs:
        return

    current_value = (doc.custom_beneficiary_purpose_of_payment or "").split("\n")
    current_value = [v.strip() for v in current_value if v.strip()]

    # Append any newly added PO refs while preserving user edits
    updated_refs = list(dict.fromkeys(current_value + po_refs))
    new_value = "\n".join(updated_refs)

    if new_value != (doc.custom_beneficiary_purpose_of_payment or ""):
        doc.custom_beneficiary_purpose_of_payment = new_value


