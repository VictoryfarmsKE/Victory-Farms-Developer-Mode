import frappe


def execute():
    """Give claims without a currency the employee's salary currency (else the company's).

    List rows format their amounts with each claim's own currency; a blank one
    falls back to the system default. Claims that already have a currency are
    not touched. Safe to run twice.
    """
    if not frappe.db.has_column("Expense Claim", "currency"):
        return

    claims = frappe.db.sql(
        "select name, employee, company from `tabExpense Claim` where ifnull(currency, '') = ''",
        as_dict=True,
    )
    for claim in claims:
        currency = frappe.db.get_value("Employee", claim.employee, "salary_currency") or (
            claim.company and frappe.get_cached_value("Company", claim.company, "default_currency")
        )
        if currency:
            frappe.db.set_value("Expense Claim", claim.name, "currency", currency, update_modified=False)
