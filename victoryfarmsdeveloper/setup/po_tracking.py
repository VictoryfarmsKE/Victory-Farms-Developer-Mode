import frappe
from frappe.utils import now_datetime

COMMENT_FIELD = "custom_procurement_comment"
UPDATED_ON_FIELD = "custom_comment_updated_on"
GROUP_FIELD = "custom_po_tracker_group"
DEPARTMENT_FIELD = "custom_department"


def update_tracking_fields(doc, method=None):
	set_tracker_group(doc)
	stamp_comment_update(doc)


def stamp_comment_update(doc, method=None):
	if doc.get(COMMENT_FIELD) and doc.has_value_changed(COMMENT_FIELD):
		doc.set(UPDATED_ON_FIELD, now_datetime())


def department_group(department):
	if not department:
		return None
	return frappe.get_cached_value("Department", department, GROUP_FIELD)


def set_tracker_group(doc):
	before = doc.get_doc_before_save()
	department_changed = before and before.get(DEPARTMENT_FIELD) != doc.get(DEPARTMENT_FIELD)
	follows_old_department = department_changed and doc.get(GROUP_FIELD) == department_group(before.get(DEPARTMENT_FIELD))

	if not doc.get(GROUP_FIELD) or follows_old_department:
		doc.set(GROUP_FIELD, department_group(doc.get(DEPARTMENT_FIELD)))
