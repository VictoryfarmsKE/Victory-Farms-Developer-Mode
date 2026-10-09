import frappe
from frappe import _
from frappe.utils import flt


RELATED_PARTY_ACCOUNT_KEYWORD = "related party"
JE_REMARK_TEMPLATE = "Auto-created from Payroll Entry {0}"


def create_journal_entry_on_submit(doc, method=None):
    """Create one consolidated Journal Entry for all submitted Salary Slips
    of this Payroll Entry.

    Debits:
        - Gross pay aggregated per cost center -> "Salaries and Wages" style
          expense account, or the matching "Due from Related Party" account
          for related-party cost centers.
        - Employer contributions (statistical deduction rows such as
          Employer NSSF / Employer Housing Levy) -> their Expense account.
    Credits:
        - Employee deductions -> their mapped Liability (payable) account.
        - Employer contributions -> their mapped Liability account.
        - The remainder (total net pay) -> Payroll Payable.
    """
    if doc.docstatus != 1:
        return

    # Guard: never create a second Journal Entry for the same Payroll Entry,
    # regardless of which event triggered this function.
    if frappe.db.exists(
        "Journal Entry",
        {"user_remark": JE_REMARK_TEMPLATE.format(doc.name), "docstatus": ["<", 2]},
    ):
        return

    company = doc.company
    payroll_payable_account = _get_payroll_payable_account(company)

    slips = frappe.get_all(
        "Salary Slip",
        filters={"payroll_entry": doc.name, "docstatus": 1},
        fields=[
            "name",
            "gross_pay",
            "employee",
        ],
    )
    if not slips:
        return

    employee_cost_centers = _get_employee_cost_centers(
        [s.employee for s in slips if s.employee]
    )

    gross_by_cost_center = {}
    credit_totals = {}  # liability account -> amount (employee deductions)
    employer_debits = {}  # expense account -> amount (employer contributions)
    employer_credits = {}  # liability account -> amount (employer contributions)
    config_errors = []

    for slip in slips:
        cost_center = _resolve_cost_center(slip, employee_cost_centers, doc)

        # Gross pay: one debit per cost center
        debit_account = _get_gross_debit_account(cost_center, company)
        gross_by_cost_center.setdefault((debit_account, cost_center), 0)
        gross_by_cost_center[(debit_account, cost_center)] += flt(slip.gross_pay)

        slip_doc = frappe.get_doc("Salary Slip", slip.name)
        for row in slip_doc.deductions:
            if not row.amount:
                continue
            accounts = _get_component_accounts(row.salary_component, company)
            if not accounts:
                continue
            if row.do_not_include_in_total:
                # Employer/statutory contribution: debit expense, credit liability
                expense_accounts = [
                    a for a in accounts if accounts[a] == "Expense"
                ]
                liability_accounts = [
                    a for a in accounts if accounts[a] == "Liability"
                ]
                if len(expense_accounts) != 1 or len(liability_accounts) != 1:
                    config_errors.append(
                        _(
                            "Salary Component {0} is a statistical deduction "
                            "used for employer contributions and must map to "
                            "exactly one Expense account and one Liability "
                            "account for company {1} (currently: {2})"
                        ).format(
                            row.salary_component,
                            company,
                            ", ".join(accounts.keys()) or _("none"),
                        )
                    )
                    continue
                employer_debits.setdefault(expense_accounts[0], 0)
                employer_debits[expense_accounts[0]] += flt(row.amount)
                employer_credits.setdefault(liability_accounts[0], 0)
                employer_credits[liability_accounts[0]] += flt(row.amount)
            else:
                liability_accounts = [
                    a for a in accounts if accounts[a] == "Liability"
                ]
                if not liability_accounts:
                    # Fall back to whatever single account is configured
                    liability_accounts = list(accounts.keys())[:1]
                credit_totals.setdefault(liability_accounts[0], 0)
                credit_totals[liability_accounts[0]] += flt(row.amount)

    if config_errors:
        frappe.throw("<br>".join(sorted(set(config_errors))))

    accounts = []
    for (account, cost_center), amount in sorted(gross_by_cost_center.items()):
        if amount:
            accounts.append(
                _je_line(
                    account,
                    debit=amount,
                    cost_center=cost_center,
                )
            )
    for account, amount in sorted(employer_debits.items()):
        if amount:
            accounts.append(_je_line(account, debit=amount))
    for account, amount in sorted(credit_totals.items()):
        if amount:
            accounts.append(_je_line(account, credit=amount))
    for account, amount in sorted(employer_credits.items()):
        if amount:
            accounts.append(_je_line(account, credit=amount))

    if not accounts:
        return

    total_debit = sum(a["debit_in_account_currency"] for a in accounts)
    total_credit = sum(a["credit_in_account_currency"] for a in accounts)
    difference = total_debit - total_credit

    if difference != 0:
        accounts.append(
            _je_line(
                payroll_payable_account,
                credit=difference if difference > 0 else 0,
                debit=abs(difference) if difference < 0 else 0,
                reference_type="Payroll Entry",
                reference_name=doc.name,
            )
        )

    remark = JE_REMARK_TEMPLATE.format(doc.name)
    je = frappe.get_doc(
        {
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "company": company,
            "posting_date": doc.posting_date,
            "accounts": accounts,
            "user_remark": remark,
            "remark": remark,
        }
    )
    je.insert(ignore_permissions=True)


def cancel_journal_entry_on_cancel(doc, method=None):
    """Remove the consolidated Journal Entry created for this Payroll Entry:
    cancel it if it was already submitted, delete it while still a draft."""
    remark = JE_REMARK_TEMPLATE.format(doc.name)
    for je in frappe.get_all(
        "Journal Entry",
        filters={"user_remark": remark, "docstatus": ["<", 2]},
        fields=["name", "docstatus"],
    ):
        if je.docstatus == 1:
            frappe.get_doc("Journal Entry", je.name).cancel()
        else:
            frappe.delete_doc("Journal Entry", je.name, ignore_permissions=True)


def create_journal_entry_if_last_slip(doc, method=None):
    """Create the consolidated Journal Entry when the last Salary Slip of a
    Payroll Entry is submitted.

    Acts as a safety net for the Payroll Entry on_submit hook: in environments
    where salary slips are submitted asynchronously (background jobs), the
    Payroll Entry hook can fire before any slip is submitted and silently skip.
    This handler runs on every Salary Slip submission and only proceeds once
    every slip of the Payroll Entry is submitted and no JE exists yet.
    """
    if doc.docstatus != 1 or not doc.payroll_entry:
        return

    pe_name = doc.payroll_entry

    # Journal Entry already created?
    if frappe.db.exists(
        "Journal Entry",
        {"user_remark": JE_REMARK_TEMPLATE.format(pe_name), "docstatus": ["<", 2]},
    ):
        return

    # Draft slips still remaining? Wait for the last one.
    if frappe.db.count("Salary Slip", {"payroll_entry": pe_name, "docstatus": 0}):
        return

    payroll_entry = frappe.get_doc("Payroll Entry", pe_name)
    if payroll_entry.docstatus != 1:
        return

    create_journal_entry_on_submit(payroll_entry)


def _je_line(
    account,
    debit=0,
    credit=0,
    cost_center=None,
    reference_type=None,
    reference_name=None,
):
    return {
        "account": account,
        "debit_in_account_currency": flt(debit),
        "credit_in_account_currency": flt(credit),
        "cost_center": cost_center,
        "reference_type": reference_type,
        "reference_name": reference_name,
        "party_type": None,
        "party": None,
    }


def _resolve_cost_center(slip, employee_cost_centers, payroll_entry):
    """Salary Slip has no cost-center columns; resolve through the
    employee's payroll cost center, falling back to the Payroll Entry's."""
    return employee_cost_centers.get(slip.get("employee")) or getattr(
        payroll_entry, "cost_center", None
    )


def _get_employee_cost_centers(employees):
    if not employees:
        return {}
    rows = frappe.get_all(
        "Employee",
        filters={"name": ["in", employees]},
        fields=["name", "payroll_cost_center"],
    )
    return {r.name: r.payroll_cost_center for r in rows if r.payroll_cost_center}


def _get_component_accounts(salary_component, company):
    """Return {account: root_type} for a Salary Component's accounts in a
    company, keyed by account name."""
    rows = frappe.get_all(
        "Salary Component Account",
        filters={"parent": salary_component, "company": company},
        fields=["account"],
    )
    result = {}
    for row in rows:
        if not row.account:
            continue
        result[row.account] = frappe.db.get_value(
            "Account", row.account, "root_type"
        )
    return result


def _get_gross_debit_account(cost_center, company):
    """Pick the debit account for gross pay of a cost center.

    Related-party cost centers (name contains 'Related Party') post to the
    matching 'Due from Related Party - <party>' receivable account; every
    other cost center posts to the Salaries & Wages expense account.
    """
    if cost_center and RELATED_PARTY_ACCOUNT_KEYWORD in cost_center.lower():
        return _match_related_party_account(cost_center, company)
    return _get_salaries_account(company)


def _match_related_party_account(cost_center, company):
    """Match a related-party cost center like 'Related Party - Sphynx - VFL'
    to the 'Due from Related Party - Sphynx' receivable account by comparing
    the trailing party name."""
    accounts = frappe.get_all(
        "Account",
        filters={
            "company": company,
            "is_group": 0,
            "account_name": ["like", "%Related Party%"],
        },
        fields=["name", "account_name"],
    )
    if not accounts:
        frappe.throw(
            _("No 'Due from Related Party' account found for company {0}").format(
                company
            )
        )

    # Tokens of the cost center name, e.g. "511010 - Related Party - Sphynx - VFL"
    # -> ["related party", "sphynx"] after dropping numeric codes and company abbr.
    tokens = [
        t.strip().lower()
        for t in cost_center.split("-")
        if t.strip() and not t.strip().isdigit()
    ]
    tokens = [t for t in tokens if t != company.lower() and t != "vfl"]
    party_tokens = [t for t in tokens if t != RELATED_PARTY_ACCOUNT_KEYWORD]

    if len(accounts) == 1:
        return accounts[0].name

    for token in sorted(party_tokens, key=len, reverse=True):
        matches = [a for a in accounts if token in a.account_name.lower()]
        if len(matches) == 1:
            return matches[0].name
        if len(matches) > 1:
            accounts = matches

    frappe.throw(
        _(
            "Cannot determine the 'Due from Related Party' account for cost "
            "center {0}. Rename the cost center so the related party name "
            "(e.g. 'Related Party - Sphynx') matches the receivable account."
        ).format(cost_center)
    )


def _get_salaries_account(company):
    """Return the Salaries & Wages expense account for the company."""
    accounts = frappe.get_all(
        "Account",
        filters={
            "company": company,
            "is_group": 0,
            "root_type": "Expense",
            "account_name": ["like", "%Salaries%Wages%"],
        },
        pluck="name",
    )
    if len(accounts) != 1:
        frappe.throw(
            _(
                "Expected exactly one 'Salaries and Wages' expense account for "
                "company {0}, found {1}: {2}"
            ).format(company, len(accounts), ", ".join(accounts) or _("none"))
        )
    return accounts[0]


def _get_payroll_payable_account(company):
    """Return the Payroll Payable account for the company."""
    company_doc = frappe.get_doc("Company", company)
    if (
        hasattr(company_doc, "default_payroll_payable_account")
        and company_doc.default_payroll_payable_account
    ):
        return company_doc.default_payroll_payable_account

    account = frappe.db.get_value(
        "Account",
        {"account_name": "Payroll Payable", "company": company, "is_group": 0},
        "name",
    )
    if not account:
        # Fall back to a payroll-liability "net pay" payable account
        account = frappe.db.get_value(
            "Account",
            {
                "account_name": ["like", "%Net pay%"],
                "company": company,
                "is_group": 0,
                "root_type": "Liability",
            },
            "name",
        )
    if not account:
        frappe.throw(
            _("Please create a 'Payroll Payable' account for company {0}").format(
                company
            )
        )
    return account
#updated: oct7
