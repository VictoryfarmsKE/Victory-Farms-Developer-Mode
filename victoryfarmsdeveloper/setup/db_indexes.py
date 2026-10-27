import frappe

LARGE_TABLE_ROWS = 100_000
LOCK_WAIT_SECONDS = 60
SHORT_LOCK_WAIT_SECONDS = 10
FIELD_INDEXES = (
	("POS Invoice", "pos_profile"),
	("Mpesa Payment Register", "transid"),
	("Sales Invoice", "status"),
)
FULLTEXT_INDEXES = (
	("Customer", "ft_customer_name", "customer_name"),
)
COMPOSITE_INDEXES = (
	("POS Invoice", "pos_profile_status_modified", ("pos_profile", "status", "modified")),
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
	("GL Entry", "is_opening_posting_date_index", ("is_opening", "posting_date")),
)
ORDERED_INDEXES = (
	("GL Entry", "posting_date_company_index", ("posting_date", "company")),
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
		for doctype, index_name, fieldnames in ORDERED_INDEXES:
			if frappe.db.table_exists(doctype):
				ensure_index_order(doctype, index_name, fieldnames)
		for doctype, index_name, fieldname in FULLTEXT_INDEXES:
			if frappe.db.table_exists(doctype) and frappe.db.has_column(doctype, fieldname):
				ensure_fulltext_index(doctype, index_name, fieldname)
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
	frappe.db.sql(f"SET SESSION lock_wait_timeout = {SHORT_LOCK_WAIT_SECONDS}")
	try:
		frappe.db.add_index(doctype, list(fieldnames), index_name=index_name)
	except Exception as e:
		print(f"Skipped index {index_name} on {doctype}, will retry on next migrate: {e}")
	finally:
		frappe.db.sql(f"SET SESSION lock_wait_timeout = {LOCK_WAIT_SECONDS}")


def ensure_index_order(doctype, index_name, fieldnames):
	if index_columns(doctype, index_name) in ([], list(fieldnames)):
		return
	columns = ", ".join(f"`{fieldname}`" for fieldname in fieldnames)
	frappe.db.sql(f"SET SESSION lock_wait_timeout = {SHORT_LOCK_WAIT_SECONDS}")
	try:
		frappe.db.sql_ddl(
			f"ALTER TABLE `tab{doctype}` DROP INDEX `{index_name}`, ADD INDEX `{index_name}` ({columns}), "
			"ALGORITHM=INPLACE, LOCK=NONE"
		)
	except Exception as e:
		print(f"Skipped reordering index {index_name} on {doctype}, will retry on next migrate: {e}")
	finally:
		frappe.db.sql(f"SET SESSION lock_wait_timeout = {LOCK_WAIT_SECONDS}")


def index_columns(doctype, index_name):
	rows = frappe.db.sql(f"SHOW INDEX FROM `tab{doctype}` WHERE Key_name = %s", (index_name,), as_dict=1)
	return [row.Column_name for row in sorted(rows, key=lambda row: row.Seq_in_index)]


def ensure_fulltext_index(doctype, index_name, fieldname):
	if frappe.db.has_index(f"tab{doctype}", index_name):
		return
	try:
		frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` ADD FULLTEXT INDEX `{index_name}` (`{fieldname}`)")
	except Exception as e:
		print(f"Skipped index {index_name} on {doctype}, will retry on next migrate: {e}")


def has_index_on(doctype, fieldname):
	return bool(
		frappe.db.sql(
			f"SHOW INDEX FROM `tab{doctype}` WHERE Column_name = %s AND Seq_in_index = 1",
			(fieldname,),
		)
	)
