import frappe

LARGE_TABLE_ROWS = 100_000


def enforce():
	doctypes = frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0, "is_virtual": 0},
		pluck="name",
	)
	for doctype in doctypes:
		if not frappe.db.table_exists(doctype):
			continue
		if frappe.db.estimate_count(doctype) <= LARGE_TABLE_ROWS:
			continue
		if has_creation_index(doctype):
			continue
		frappe.db.add_index(doctype, ["creation"], index_name="creation")


def has_creation_index(doctype):
	return bool(
		frappe.db.sql(
			f"SHOW INDEX FROM `tab{doctype}` WHERE Column_name = 'creation' AND Seq_in_index = 1"
		)
	)
