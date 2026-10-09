import hashlib
import inspect

import frappe
from erpnext.accounts.report import financial_statements
from frappe.query_builder.functions import Sum
from pypika.terms import ExistsCriterion

DAILY_TOTAL_ROOT_TYPES = ("Income", "Expense")
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
		.force_index("posting_date_company_index")
	)

	ignore_is_opening = frappe.db.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting")
	if ignore_opening_entries and not ignore_is_opening:
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
