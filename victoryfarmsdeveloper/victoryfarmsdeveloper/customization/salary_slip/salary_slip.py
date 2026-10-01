import frappe


def sync_additional_salary_notes(doc, method=None):
    """Copy the Note field from Additional Salary to Salary Slip earning/deduction rows.

    When Additional Salary entries are included in a Salary Slip, this function
    transfers the custom_note from each linked Additional Salary record to the
    corresponding earning or deduction row on the Salary Slip.
    """
    for row in doc.earnings:
        _copy_note_from_additional_salary(row)

    for row in doc.deductions:
        _copy_note_from_additional_salary(row)


def _copy_note_from_additional_salary(row):
    """Fetch the note from the linked Additional Salary and set it on the row.

    Each Salary Slip Earning/Deduction row may have an ``additional_salary``
    field linking back to the Additional Salary document.  If that link exists
    and the Additional Salary has a ``custom_note``, we copy it onto the row.
    """
    additional_salary_name = getattr(row, "additional_salary", None)
    if not additional_salary_name:
        return

    note = frappe.db.get_value("Additional Salary", additional_salary_name, "custom_note")
    if note and row.custom_note != note:
        frappe.db.set_value(row.doctype, row.name, "custom_note", note)
        row.custom_note = note
