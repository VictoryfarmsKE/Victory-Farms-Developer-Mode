import functools

from victoryfarmsdeveloper.setup import (
	employee_saves,
	financial_statement_totals,
	general_ledger_opening,
	pos_closing_commits,
	stock_warehouse_filter,
	trial_balance_totals,
)


def install_all():
	install_once()


@functools.cache
def install_once():
	financial_statement_totals.install()
	trial_balance_totals.install()
	employee_saves.install()
	stock_warehouse_filter.install()
	general_ledger_opening.install()
	pos_closing_commits.install()
