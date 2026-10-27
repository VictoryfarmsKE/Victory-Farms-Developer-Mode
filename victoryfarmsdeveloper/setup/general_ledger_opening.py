import hashlib
import inspect

import frappe
from erpnext.accounts.report.general_ledger import general_ledger
from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency
from frappe.utils import date_diff, nowdate

EXPECTED_SOURCE_SHA256 = "5e1be54cebb50c82408bb357f9cd8b8b49e8b5c5adeede29392af66c373c618a"
original_get_gl_entries = general_ledger.get_gl_entries
RECENT_DAYS = 400
SUMMED_FIELDS = ("debit", "credit", "debit_in_account_currency", "credit_in_account_currency")
FROM_DATE_OR_OPENING = "(posting_date >=%(from_date)s or is_opening = 'Yes')"
TO_DATE_OR_OPENING = "(posting_date <=%(to_date)s or is_opening = 'Yes')"
OPENING_INDEX = "is_opening_posting_date_index"


def watched_sources():
	return (
		general_ledger.get_gl_entries,
		general_ledger.get_conditions,
		general_ledger.get_accountwise_gle,
		general_ledger.initialize_gle_map,
		general_ledger.get_data_with_opening_closing,
	)


def reads_history(filters):
	return bool(
		filters.get("account")
		or filters.get("party")
		or filters.get("categorize_by") in ("Categorize by Account", "Categorize by Party")
	)


def can_sum_opening(filters):
	return (
		reads_history(filters)
		and filters.get("categorize_by") != "Categorize by Party"
		and not filters.get("disable_opening_balance_calculation")
		and filters.get("from_date")
	)


def can_split_opening_rows(filters):
	return (
		not reads_history(filters)
		and filters.get("from_date")
		and filters.get("to_date")
		and not frappe.db.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting")
		and frappe.db.has_index("tabGL Entry", OPENING_INDEX)
	)


def get_gl_entries(filters, accounting_dimensions):
	if can_sum_opening(filters):
		return read_gl_entries(filters, accounting_dimensions, opening_sum_query)
	if can_split_opening_rows(filters):
		return read_gl_entries(filters, accounting_dimensions, opening_rows_query)
	return original_get_gl_entries(filters, accounting_dimensions)


def read_gl_entries(filters, accounting_dimensions, build_query):
	currency_map = get_currency(filters)
	if filters.get("include_default_book_entries"):
		filters["company_fb"] = frappe.get_cached_value(
			"Company", filters.get("company"), "default_finance_book"
		)
	columns = selected_columns(filters, accounting_dimensions)
	conditions = general_ledger.get_conditions(filters)
	gl_entries = frappe.db.sql(build_query(filters, columns, conditions), filters, as_dict=1)

	party_name_map = general_ledger.get_party_name_map()
	for gl_entry in gl_entries:
		if gl_entry.party_type and gl_entry.party:
			gl_entry.party_name = party_name_map.get(gl_entry.party_type, {}).get(gl_entry.party)

	if filters.get("presentation_currency"):
		return convert_to_presentation_currency(gl_entries, currency_map, filters)
	return gl_entries


def opening_sum_query(filters, columns, conditions):
	in_period = ", ".join(expression for _name, expression, _opening in columns)
	before_period = ", ".join(opening for _name, _expression, opening in columns)
	return f"""
		select {in_period}
		from `tabGL Entry` {period_index(filters)}
		where company=%(company)s {conditions} and posting_date >= %(from_date)s
		union all
		select {before_period}
		from `tabGL Entry`
		where company=%(company)s {conditions} and posting_date < %(from_date)s
		group by account, account_currency
		{order_by(filters)}
	"""


def opening_rows_query(filters, columns, conditions):
	fields = ", ".join(expression for _name, expression, _opening in columns)
	in_period = conditions.replace(FROM_DATE_OR_OPENING, "posting_date >= %(from_date)s").replace(
		TO_DATE_OR_OPENING, "posting_date <= %(to_date)s"
	)
	opening_outside_period = conditions.replace(FROM_DATE_OR_OPENING, "is_opening = 'Yes'").replace(
		TO_DATE_OR_OPENING, "(posting_date < %(from_date)s or posting_date > %(to_date)s)"
	)
	return f"""
		select {fields}
		from `tabGL Entry`
		where company=%(company)s {in_period}
		union all
		select {fields}
		from `tabGL Entry`
		where company=%(company)s {opening_outside_period}
		{order_by(filters)}
	"""


def period_index(filters):
	if date_diff(nowdate(), filters.get("from_date")) <= RECENT_DAYS and date_index_leads():
		return "force index (posting_date_company_index)"
	return ""


def date_index_leads():
	first_column = frappe.db.sql(
		"""
		show index from `tabGL Entry`
		where Key_name = 'posting_date_company_index' and Seq_in_index = 1
	""",
		as_dict=1,
	)
	return bool(first_column) and first_column[0].Column_name == "posting_date"


def selected_columns(filters, accounting_dimensions):
	columns = [
		("gl_entry", "name as gl_entry", "null as gl_entry"),
		("posting_date", "posting_date", "min(posting_date) as posting_date"),
		("account", "account", "account"),
		("party_type", "party_type", "null as party_type"),
		("party", "party", "null as party"),
		("voucher_type", "voucher_type", "null as voucher_type"),
		("voucher_subtype", "voucher_subtype", "null as voucher_subtype"),
		("voucher_no", "voucher_no", "null as voucher_no"),
	]
	columns += [(dimension, dimension, f"null as {dimension}") for dimension in accounting_dimensions]
	columns += [
		("cost_center", "cost_center", "null as cost_center"),
		("project", "project", "null as project"),
	]
	if filters.get("add_values_in_transaction_currency"):
		columns += [
			(
				"debit_in_transaction_currency",
				"debit_in_transaction_currency",
				"sum(debit_in_transaction_currency) as debit_in_transaction_currency",
			),
			(
				"credit_in_transaction_currency",
				"credit_in_transaction_currency",
				"sum(credit_in_transaction_currency) as credit_in_transaction_currency",
			),
			("transaction_currency", "transaction_currency", "null as transaction_currency"),
		]
	columns += [
		("against_voucher_type", "against_voucher_type", "null as against_voucher_type"),
		("against_voucher", "against_voucher", "null as against_voucher"),
		("account_currency", "account_currency", "account_currency"),
		("against", "against", "null as against"),
		("is_opening", "is_opening", "'No' as is_opening"),
		("creation", "creation", "min(creation) as creation"),
	]
	columns += [(field, field, f"sum({field}) as {field}") for field in SUMMED_FIELDS]
	if filters.get("show_remarks"):
		remarks_length = frappe.db.get_single_value("Accounts Settings", "general_ledger_remarks_length")
		remarks = f"substr(remarks, 1, {int(remarks_length)}) as remarks" if remarks_length else "remarks"
		columns.append(("remarks", remarks, "null as remarks"))
	return columns


def order_by(filters):
	order = "order by posting_date, account, creation"
	if filters.get("include_dimensions"):
		order = "order by posting_date, creation"
	if filters.get("categorize_by") == "Categorize by Voucher":
		return "order by posting_date, voucher_type, voucher_no"
	if filters.get("categorize_by") == "Categorize by Account":
		return "order by account, posting_date, creation"
	return order


def source_sha256():
	source = "".join(inspect.getsource(fn) for fn in watched_sources())
	return hashlib.sha256(source.encode()).hexdigest()


def source_matches():
	try:
		return source_sha256() == EXPECTED_SOURCE_SHA256
	except (OSError, TypeError):
		return False


def install():
	if source_matches():
		general_ledger.get_gl_entries = get_gl_entries


def is_installed():
	return general_ledger.get_gl_entries is get_gl_entries


def check():
	install()
	if is_installed():
		return []
	problems = ["ERPNext General Ledger report changed, it reads every older row for the opening balance again"]
	frappe.log_error(title="General ledger opening check failed", message="\n".join(problems))
	return problems
