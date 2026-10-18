import hashlib
import inspect
import re

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from erpnext.accounts.report import financial_statements
from frappe import _
from frappe.query_builder import Field
from frappe.query_builder.functions import Max, Sum
from frappe.utils import cstr
from pypika.terms import Criterion, ExistsCriterion

from victoryfarmsdeveloper.setup import gl_day_totals

DAILY_TOTAL_ROOT_TYPES = ("Income", "Expense")
TOTALS_MATCH_FIELDS = ("company", "account", "cost_center", "finance_book")
EXPECTED_SOURCE_SHA256 = "a5b1c6048d581c94ffd432c5209f74d98b0b888f8869de1e4421ed75417790d6"
original_get_accounting_entries = financial_statements.get_accounting_entries


def get_accounting_entries(
	doctype,
	from_date,
	to_date,
	filters,
	root_lft=None,
	root_rgt=None,
	root_type=None,
	ignore_closing_entries=None,
	period_closing_voucher=None,
	ignore_opening_entries=False,
	group_by_account=False,
):
	if root_lft and root_rgt and not root_belongs_to_company(root_lft, root_rgt, filters.company):
		return []

	if doctype == "GL Entry" and day_totals_cover(filters):
		if not group_by_account:
			return entries_from_day_totals(
				from_date,
				to_date,
				filters,
				root_lft,
				root_rgt,
				root_type,
				ignore_closing_entries,
				ignore_opening_entries,
			)
		if group_by_account and grouped_totals_allowed(filters):
			return entries_by_account_from_day_totals(
				from_date,
				to_date,
				filters,
				root_lft,
				root_rgt,
				root_type,
				ignore_closing_entries,
				ignore_opening_entries,
			)

	if doctype != "GL Entry" or group_by_account or root_type not in DAILY_TOTAL_ROOT_TYPES:
		return original_get_accounting_entries(
			doctype,
			from_date,
			to_date,
			filters,
			root_lft=root_lft,
			root_rgt=root_rgt,
			root_type=root_type,
			ignore_closing_entries=ignore_closing_entries,
			period_closing_voucher=period_closing_voucher,
			ignore_opening_entries=ignore_opening_entries,
			group_by_account=group_by_account,
		)

	return daily_gl_totals(
		from_date,
		to_date,
		filters,
		root_lft,
		root_rgt,
		root_type,
		ignore_closing_entries,
		ignore_opening_entries,
	)


def daily_gl_totals(
	from_date,
	to_date,
	filters,
	root_lft,
	root_rgt,
	root_type,
	ignore_closing_entries,
	ignore_opening_entries,
	posting_dates=None,
):
	doctype = "GL Entry"
	gl_entry = frappe.qb.DocType(doctype)
	query = (
		frappe.qb.from_(gl_entry)
		.select(
			gl_entry.account,
			Sum(gl_entry.debit).as_("debit"),
			Sum(gl_entry.credit).as_("credit"),
			Sum(gl_entry.debit_in_account_currency).as_("debit_in_account_currency"),
			Sum(gl_entry.credit_in_account_currency).as_("credit_in_account_currency"),
			gl_entry.account_currency,
			gl_entry.posting_date,
			gl_entry.is_opening,
			gl_entry.fiscal_year,
		)
		.where(gl_entry.company == filters.company)
		.where(gl_entry.is_cancelled == 0)
		.where(gl_entry.posting_date <= to_date)
	)

	if posting_dates is None:
		query = query.force_index("posting_date_company_index")
	else:
		query = query.where(gl_entry.posting_date.isin(posting_dates))

	if ignore_opening_entries and not ignore_is_opening_check():
		query = query.where(gl_entry.is_opening == "No")

	query = financial_statements.apply_additional_conditions(
		doctype, query, from_date, ignore_closing_entries, filters
	)

	if (root_lft and root_rgt) or root_type:
		account_filter_query = financial_statements.get_account_filter_query(
			root_lft, root_rgt, root_type, gl_entry
		)
		query = query.where(ExistsCriterion(account_filter_query))

	from frappe.desk.reportview import build_match_conditions

	query, params = query.walk()
	match_conditions = build_match_conditions(doctype)

	if match_conditions:
		query += "and" + match_conditions

	query += " GROUP BY `account`, `posting_date`, `is_opening`, `fiscal_year`, `account_currency`"

	return frappe.db.sql(query, params, as_dict=True)


def day_totals_cover(filters):
	if not filters or filters.get("project") or not gl_day_totals.is_ready():
		return False

	if any(filters.get(dimension.fieldname) for dimension in get_accounting_dimensions(as_list=False)):
		return False

	return totals_match_conditions() is not None


def gl_match_conditions():
	from frappe.desk.reportview import build_match_conditions

	return build_match_conditions("GL Entry")


def totals_match_conditions():
	conditions = gl_match_conditions()
	if not conditions:
		return ""
	fields = set(re.findall(r"`tabGL Entry`\.`(\w+)`", conditions))
	rest = re.sub(r"`tabGL Entry`\.`\w+`", "", conditions)
	if "`" in rest or not fields <= set(TOTALS_MATCH_FIELDS):
		return None
	return conditions.replace("`tabGL Entry`.", f"`{gl_day_totals.TABLE}`.")


class RawCondition(Criterion):
	def __init__(self, sql):
		super().__init__()
		self.sql = sql

	def get_sql(self, **kwargs):
		return f"({self.sql})"


def grouped_totals_allowed(filters):
	from victoryfarmsdeveloper.setup import trial_balance_totals

	return trial_balance_totals.is_installed() and not filters.get("presentation_currency")


def live_dates_between(company, from_date, to_date):
	return sorted(
		d
		for d in gl_day_totals.live_dates(company)
		if d <= frappe.utils.getdate(to_date) and (not from_date or d >= frappe.utils.getdate(from_date))
	)


def day_totals_query(
	totals,
	from_date,
	to_date,
	filters,
	root_lft,
	root_rgt,
	root_type,
	ignore_closing_entries,
	ignore_opening_entries,
	live_dates,
):
	query = (
		frappe.qb.from_(totals).where(totals.company == filters.company).where(totals.posting_date <= to_date)
	)

	if from_date:
		query = query.where(totals.posting_date >= from_date)

	if live_dates:
		query = query.where(totals.posting_date.notin(live_dates))

	if ignore_opening_entries and not ignore_is_opening_check():
		query = query.where(totals.is_opening == "No")

	if ignore_closing_entries:
		query = query.where(totals.is_closing == 0)

	if filters.get("cost_center"):
		filters.cost_center = financial_statements.get_cost_centers_with_children(filters.cost_center)
		query = query.where(totals.cost_center.isin(filters.cost_center))

	query = query.where(totals.finance_book.isin(finance_books(filters)))

	if (root_lft and root_rgt) or root_type:
		accounts = leaf_accounts(root_lft, root_rgt, root_type)
		if not accounts:
			return None
		query = query.where(totals.account.isin(accounts))

	match_conditions = totals_match_conditions()
	if match_conditions:
		query = query.where(RawCondition(match_conditions))

	return query


def entries_from_day_totals(
	from_date,
	to_date,
	filters,
	root_lft,
	root_rgt,
	root_type,
	ignore_closing_entries,
	ignore_opening_entries,
):
	live_dates = live_dates_between(filters.company, from_date, to_date)

	totals = frappe.qb.Table(gl_day_totals.TABLE)
	query = day_totals_query(
		totals,
		from_date,
		to_date,
		filters,
		root_lft,
		root_rgt,
		root_type,
		ignore_closing_entries,
		ignore_opening_entries,
		live_dates,
	)
	if query is None:
		return []

	query = query.select(
		totals.account,
		Sum(totals.debit).as_("debit"),
		Sum(totals.credit).as_("credit"),
		Sum(totals.debit_in_account_currency).as_("debit_in_account_currency"),
		Sum(totals.credit_in_account_currency).as_("credit_in_account_currency"),
		totals.account_currency,
		totals.posting_date,
		totals.is_opening,
		totals.fiscal_year,
	).groupby(totals.account, totals.posting_date, totals.is_opening, totals.fiscal_year, totals.account_currency)

	entries = [blank_to_none(row) for row in query.run(as_dict=True)]

	if live_dates:
		entries += daily_gl_totals(
			from_date,
			to_date,
			filters,
			root_lft,
			root_rgt,
			root_type,
			ignore_closing_entries,
			ignore_opening_entries,
			posting_dates=live_dates,
		)
		entries.sort(key=grouped_order)

	return entries


def grouped_order(entry):
	return (
		entry.posting_date,
		cstr(entry.is_opening),
		cstr(entry.fiscal_year),
		cstr(entry.account_currency),
	)


def entries_by_account_from_day_totals(
	from_date,
	to_date,
	filters,
	root_lft,
	root_rgt,
	root_type,
	ignore_closing_entries,
	ignore_opening_entries,
):
	live_dates = live_dates_between(filters.company, from_date, to_date)

	totals = frappe.qb.Table(gl_day_totals.TABLE)
	query = day_totals_query(
		totals,
		from_date,
		to_date,
		filters,
		root_lft,
		root_rgt,
		root_type,
		ignore_closing_entries,
		ignore_opening_entries,
		live_dates,
	)
	if query is None:
		return []
	query = query.select(*amount_columns(totals))

	if live_dates:
		gl_entry = frappe.qb.DocType("GL Entry")
		live = (
			frappe.qb.from_(gl_entry)
			.select(*amount_columns(gl_entry))
			.where(gl_entry.company == filters.company)
			.where(gl_entry.is_cancelled == 0)
			.where(gl_entry.posting_date <= to_date)
			.where(gl_entry.posting_date.isin(live_dates))
		)
		if ignore_opening_entries and not ignore_is_opening_check():
			live = live.where(gl_entry.is_opening == "No")
		live = financial_statements.apply_additional_conditions(
			"GL Entry", live, from_date, ignore_closing_entries, filters
		)
		if (root_lft and root_rgt) or root_type:
			live = live.where(
				ExistsCriterion(
					financial_statements.get_account_filter_query(root_lft, root_rgt, root_type, gl_entry)
				)
			)
		match_conditions = gl_match_conditions()
		if match_conditions:
			live = live.where(RawCondition(match_conditions))
		query = query.union_all(live)

	return summed_by_account(query, ("posting_date", "is_opening", "fiscal_year"))


def amount_columns(table):
	return (
		table.account,
		table.account_currency,
		table.posting_date,
		table.is_opening,
		table.fiscal_year,
		table.debit,
		table.credit,
		table.debit_in_account_currency,
		table.credit_in_account_currency,
	)


def summed_by_account(query, extra_fields=()):
	rows = frappe.qb.from_(query).select(
		Field("account"),
		Max(Field("account_currency")).as_("account_currency"),
		*(Max(Field(fieldname)).as_(fieldname) for fieldname in extra_fields),
		Sum(Field("debit")).as_("debit"),
		Sum(Field("credit")).as_("credit"),
		Sum(Field("debit_in_account_currency")).as_("debit_in_account_currency"),
		Sum(Field("credit_in_account_currency")).as_("credit_in_account_currency"),
	).groupby(Field("account"))
	return [blank_to_none(row) for row in rows.run(as_dict=True)]


def finance_books(filters):
	books = [cstr(filters.finance_book), ""]
	if filters.get("include_default_book_entries"):
		company_fb = frappe.get_cached_value("Company", filters.company, "default_finance_book")
		if filters.finance_book and company_fb and cstr(filters.finance_book) != cstr(company_fb):
			frappe.throw(_("To use a different finance book, please uncheck 'Include Default FB Entries'"))
		books.append(cstr(company_fb))
	return list(dict.fromkeys(books))


def leaf_accounts(root_lft, root_rgt, root_type):
	filters = {"is_group": 0}
	if root_lft and root_rgt:
		filters["lft"] = (">=", root_lft)
		filters["rgt"] = ("<=", root_rgt)
	if root_type:
		filters["root_type"] = root_type
	return frappe.get_all("Account", filters=filters, pluck="name")


def blank_to_none(row):
	for fieldname in ("account_currency", "is_opening", "fiscal_year"):
		if row.get(fieldname) == "":
			row[fieldname] = None
	return row


def ignore_is_opening_check():
	return frappe.db.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting")


def root_belongs_to_company(root_lft, root_rgt, company):
	root_company = frappe.db.get_value("Account", {"lft": root_lft, "rgt": root_rgt}, "company")
	return not root_company or root_company == company


def source_matches():
	source = inspect.getsource(original_get_accounting_entries)
	return hashlib.sha256(source.encode()).hexdigest() == EXPECTED_SOURCE_SHA256


def install():
	if source_matches():
		financial_statements.get_accounting_entries = get_accounting_entries


def is_installed():
	return financial_statements.get_accounting_entries is get_accounting_entries


def check():
	if is_installed():
		return []
	problems = [
		"ERPNext financial_statements.get_accounting_entries changed, daily totals for P&L, Balance Sheet and Cash Flow are off"
	]
	frappe.log_error(title="Financial statement totals check failed", message="\n".join(problems))
	return problems
