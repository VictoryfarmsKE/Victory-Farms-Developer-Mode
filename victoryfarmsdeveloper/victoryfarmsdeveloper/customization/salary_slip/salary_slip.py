import frappe
from frappe import _


def create_journal_entry_on_submit(doc, method=None):
    """Auto-create a Journal Entry when a Salary Slip is submitted.

    For each earning component, the configured expense account is debited.
    For each deduction component, the configured payable account is credited.
    The net pay difference is posted to the Payroll Payable account.
    """
    if doc.docstatus != 1:
        return

    # Skip if a Journal Entry is already linked (e.g., created from Payroll Entry)
    if doc.journal_entry:
        return

    company = doc.company
    payroll_payable_account = _get_payroll_payable_account(company)
    cost_center = getattr(doc, "payroll_cost_center", None) or getattr(doc, "cost_center", None) or None

    accounts = []

    # Earnings: debit the expense account for each component
    for row in doc.earnings:
        if row.amount and not row.do_not_include_in_total:
            account = _get_component_account(row.salary_component, company)
            if account:
                accounts.append({
                    "account": account,
                    "debit_in_account_currency": abs(row.amount),
                    "credit_in_account_currency": 0,
                    "cost_center": cost_center,
                    "reference_type": "Salary Slip",
                    "reference_name": doc.name,
                    "party_type": None,
                    "party": None,
                })

    # Deductions: credit the payable account for each component
    for row in doc.deductions:
        if row.amount and not row.do_not_include_in_total:
            account = _get_component_account(row.salary_component, company)
            if account:
                accounts.append({
                    "account": account,
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": abs(row.amount),
                    "cost_center": cost_center,
                    "reference_type": "Salary Slip",
                    "reference_name": doc.name,
                    "party_type": None,
                    "party": None,
                })

    if not accounts:
        return

    # Calculate net pay difference and post to payroll payable
    total_debit = sum(a["debit_in_account_currency"] for a in accounts)
    total_credit = sum(a["credit_in_account_currency"] for a in accounts)
    difference = total_debit - total_credit

    if difference != 0:
        accounts.append({
            "account": payroll_payable_account,
            "debit_in_account_currency": 0 if difference > 0 else abs(difference),
            "credit_in_account_currency": difference if difference > 0 else 0,
            "cost_center": cost_center,
            "reference_type": "Salary Slip",
            "reference_name": doc.name,
            "party_type": "Employee",
            "party": doc.employee,
        })

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "company": company,
        "posting_date": doc.end_date,
        "accounts": accounts,
        "user_remark": "Auto-created from Salary Slip {0} for {1}".format(doc.name, doc.employee_name),
        "remark": "Salary Slip {0} - {1}".format(doc.name, doc.employee_name),
    })

    je.insert(ignore_permissions=True)
    je.submit()

    frappe.db.set_value("Salary Slip", doc.name, "journal_entry", je.name)


def unlink_journal_entry_on_cancel(doc, method=None):
    """Clear the journal_entry link on salary slip cancellation."""
    if doc.journal_entry:
        frappe.db.set_value("Salary Slip", doc.name, "journal_entry", "")


def _get_component_account(salary_component, company):
    """Return the account linked to a Salary Component for the given company."""
    account = frappe.db.get_value(
        "Salary Component Account",
        {"parent": salary_component, "company": company},
        "account",
    )
    return account


def _get_payroll_payable_account(company):
    """Return the Payroll Payable account for the company.

    Falls back to the company's default Payroll Payable account if set,
    otherwise searches for any account named 'Payroll Payable' under the company.
    """
    company_doc = frappe.get_doc("Company", company)
    if hasattr(company_doc, "default_payroll_payable_account") and company_doc.default_payroll_payable_account:
        return company_doc.default_payroll_payable_account

    account = frappe.db.get_value(
        "Account",
        {"account_name": "Payroll Payable", "company": company, "is_group": 0},
        "name",
    )
    if not account:
        frappe.throw(
            _("Please create a 'Payroll Payable' account for company {0}").format(company)
        )
    return account