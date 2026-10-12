import functools

from victoryfarmsdeveloper.setup import employee_saves, financial_statement_totals


def install_all():
	install_once()


@functools.cache
def install_once():
	financial_statement_totals.install()
	employee_saves.install()
