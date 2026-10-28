import frappe

from victoryfarmsdeveloper.setup.farm_po_tracker_email import EMAIL_GROUP


def execute():
	if frappe.db.exists("Email Group", EMAIL_GROUP):
		return
	frappe.get_doc({"doctype": "Email Group", "title": EMAIL_GROUP}).insert(ignore_permissions=True)
