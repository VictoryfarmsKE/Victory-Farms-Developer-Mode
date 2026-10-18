import hashlib
import inspect

import frappe
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.accounts.report.trial_balance import trial_balance
from frappe.utils import flt

from victoryfarmsdeveloper.setup import financial_statement_totals, gl_day_totals

EXPECTED_SOURCE_SHA256 = "8355e74544236715b817a3c25db95dfbe6e62bfce8dbfb277d974b4ca47282a1"
original_get_opening_balance = trial_balance.get_opening_balance


def watched_sources():
	return (
		trial_balance.get_data,
		trial_balance.get_rootwise_opening_balances,
		original_get_opening_balance,
		trial_balance.calculate_values,
	)


def get_opening_balance(
	doctype,
	filters,
	report_type,
	accounting_dimensions,
	period_closing_voucher=None,
	start_date=None,
	ignore_is_opening=0,
):
	if (
		doctype != "GL Entry"
		or filters.get("presentation_currency")
		or not financial_statement_totals.day_totals_cover(filters)
	):
		return original_get_opening_balance(
			doctype,
			filters,
			report_type,
			accounting_dimensions,
			period_closing_voucher=period_closing_voucher,
			start_date=start_date,
			ignore_is_opening=ignore_is_opening,
		)

	accounts = frappe.db.get_all("Account", filters={"report_type": report_type}, pluck="name")
	if not accounts:
		return []

	live_dates = sorted(gl_day_totals.live_dates(filters.company) or [])

	totals = frappe.qb.Table(gl_day_totals.TABLE)
	query = opening_query(totals, filters, report_type, accounts, start_date, ignore_is_opening)
	if not flt(filters.with_period_closing_entry_for_opening):
		query = query.where(totals.is_closing == 0)
	if live_dates:
		query = query.where(totals.posting_date.notin(live_dates))
		gl_entry = frappe.qb.DocType("GL Entry")
		live = opening_query(gl_entry, filters, report_type, accounts, start_date, ignore_is_opening)
		live = live.where(gl_entry.is_cancelled == 0).where(gl_entry.posting_date.isin(live_dates))
		if not flt(filters.with_period_closing_entry_for_opening):
			live = live.where(gl_entry.voucher_type != "Period Closing Voucher")
		query = query.union_all(live)

	return financial_statement_totals.summed_by_account(query)


def opening_query(table, filters, report_type, accounts, start_date, ignore_is_opening):
	query = (
		frappe.qb.from_(table)
		.select(
			table.account,
			table.account_currency,
			table.debit,
			table.credit,
			table.debit_in_account_currency,
			table.credit_in_account_currency,
		)
		.where(table.company == filters.company)
		.where(table.account.isin(accounts))
	)

	if start_date:
		query = query.where((table.posting_date >= start_date) & (table.posting_date < filters.from_date))
		if not ignore_is_opening:
			query = query.where(table.is_opening == "No")
	elif ignore_is_opening:
		query = query.where(table.posting_date < filters.from_date)
	else:
		query = query.where((table.posting_date < filters.from_date) | (table.is_opening == "Yes"))

	if not filters.show_unclosed_fy_pl_balances and report_type == "Profit and Loss":
		query = query.where(table.posting_date >= filters.year_start_date)

	if filters.cost_center:
		query = query.where(table.cost_center.isin(get_cost_centers_with_children(filters.get("cost_center"))))

	if frappe.db.count("Finance Book"):
		query = query.where(table.finance_book.isin(financial_statement_totals.finance_books(filters)))

	return query


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
		trial_balance.get_opening_balance = get_opening_balance


def is_installed():
	return trial_balance.get_opening_balance is get_opening_balance


def check():
	install()
	if is_installed():
		return []
	problems = ["ERPNext Trial Balance report changed, it reads every older GL row for opening balances again"]
	frappe.log_error(title="Trial balance totals check failed", message="\n".join(problems))
	return problems
