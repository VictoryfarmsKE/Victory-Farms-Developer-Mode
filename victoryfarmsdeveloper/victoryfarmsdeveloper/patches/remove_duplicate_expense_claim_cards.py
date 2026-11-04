import frappe

DUPLICATE_CARDS = ("Claims Approved (This Month)", "Claims Rejected (This Month)")


def execute():
    """Delete our Approved/Rejected number cards, which duplicate HRMS's own.

    Fixtures only add and update, never delete. HRMS's cards read approval_status,
    which is kept truthful, so they are the single source. Safe to run twice.
    """
    frappe.db.delete("Number Card Link", {"card": ("in", DUPLICATE_CARDS)})
    for name in DUPLICATE_CARDS:
        frappe.delete_doc("Number Card", name, ignore_missing=True, force=True)
