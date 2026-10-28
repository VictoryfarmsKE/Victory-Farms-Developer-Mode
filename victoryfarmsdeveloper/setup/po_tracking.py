from frappe.utils import now_datetime

COMMENT_FIELD = "custom_procurement_comment"
UPDATED_ON_FIELD = "custom_comment_updated_on"


def stamp_comment_update(doc, method=None):
	if doc.get(COMMENT_FIELD) and doc.has_value_changed(COMMENT_FIELD):
		doc.set(UPDATED_ON_FIELD, now_datetime())
