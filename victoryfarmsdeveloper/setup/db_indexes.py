import frappe

LARGE_TABLE_ROWS = 100_000
LOCK_WAIT_SECONDS = 60
FIELD_INDEXES = (
	("POS Invoice", "pos_profile"),
	("Mpesa Payment Register", "transid"),
)
COMPOSITE_INDEXES = (
	(
		"GL Entry",
		"gl_month_summary_index",
		(
			"posting_date",
			"docstatus",
			"is_cancelled",
			"account",
			"cost_center",
			"debit_in_account_currency",
			"credit_in_account_currency",
		),
	),
)


def enforce():
	previous_wait = frappe.db.sql("SELECT @@SESSION.lock_wait_timeout")[0][0]
	frappe.db.sql(f"SET SESSION lock_wait_timeout = {LOCK_WAIT_SECONDS}")
	try:
		for doctype in large_doctypes():
			ensure_index(doctype, "creation", "creation")
		for doctype, fieldname in FIELD_INDEXES:
			if frappe.db.table_exists(doctype) and frappe.db.has_column(doctype, fieldname):
				ensure_index(doctype, fieldname, f"{fieldname}_index")
		for doctype, index_name, fieldnames in COMPOSITE_INDEXES:
			if frappe.db.table_exists(doctype):
				ensure_composite_index(doctype, index_name, fieldnames)
	finally:
		frappe.db.sql(f"SET SESSION lock_wait_timeout = {int(previous_wait)}")


def large_doctypes():
	doctypes = frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0, "is_virtual": 0},
		pluck="name",
	)
	return [
		doctype
		for doctype in doctypes
		if frappe.db.table_exists(doctype) and frappe.db.estimate_count(doctype) > LARGE_TABLE_ROWS
	]


def ensure_index(doctype, fieldname, index_name):
	if has_index_on(doctype, fieldname):
		return
	try:
		frappe.db.add_index(doctype, [fieldname], index_name=index_name)
	except Exception as e:
		print(f"Skipped index {index_name} on {doctype}, will retry on next migrate: {e}")


def ensure_composite_index(doctype, index_name, fieldnames):
	if frappe.db.has_index(f"tab{doctype}", index_name):
		return
	try:
		frappe.db.add_index(doctype, list(fieldnames), index_name=index_name)
	except Exception as e:
		print(f"Skipped index {index_name} on {doctype}, will retry on next migrate: {e}")


def has_index_on(doctype, fieldname):
	return bool(
		frappe.db.sql(
			f"SHOW INDEX FROM `tab{doctype}` WHERE Column_name = %s AND Seq_in_index = 1",
			(fieldname,),
		)
	)
