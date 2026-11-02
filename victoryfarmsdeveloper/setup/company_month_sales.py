import inspect

import frappe
from erpnext.accounts.doctype.sales_invoice import sales_invoice as sales_invoice_module
from erpnext.setup.doctype.company import company as company_module

PENDING_KEY = "company_month_sales_pending"
CALL_SITE = "update_company_current_month_sales(self.company)"
REFRESH_METHOD = "victoryfarmsdeveloper.setup.company_month_sales.refresh"


def update_company_current_month_sales(company):
	pending = frappe.local.flags.get(PENDING_KEY)
	if pending is None:
		pending = frappe.local.flags[PENDING_KEY] = set()
		frappe.db.after_commit.add(enqueue_pending)
		frappe.db.after_rollback.add(clear_pending)
	pending.add(company)


def enqueue_pending():
	for company in sorted(frappe.local.flags.pop(PENDING_KEY, None) or ()):
		try:
			frappe.enqueue(
				REFRESH_METHOD,
				queue="short",
				job_id=f"company_month_sales::{company}",
				deduplicate=True,
				company=company,
			)
		except Exception:
			company_module.update_company_current_month_sales(company)


def clear_pending():
	frappe.local.flags.pop(PENDING_KEY, None)


def refresh(company):
	company_module.update_company_current_month_sales(company)


def call_site_present():
	try:
		source = inspect.getsource(sales_invoice_module.SalesInvoice.on_submit) + inspect.getsource(
			sales_invoice_module.SalesInvoice.on_cancel
		)
	except (OSError, TypeError):
		return False
	return source.count(CALL_SITE) == 2


def install():
	if call_site_present():
		sales_invoice_module.update_company_current_month_sales = update_company_current_month_sales


def is_installed():
	return (
		call_site_present()
		and sales_invoice_module.update_company_current_month_sales is update_company_current_month_sales
	)


def check():
	install()
	if is_installed():
		return []
	problems = [
		"ERPNext Sales Invoice changed how it updates monthly sales, invoice saves may lock the Company row again"
	]
	frappe.log_error(title="Company month sales check failed", message="\n".join(problems))
	return problems
