import frappe
from erpnext.setup.utils import get_exchange_rate
from frappe import _
from frappe.utils import flt

MAX_DEVIATION_PCT = 10


def apply_bank_cross_rate(doc, method=None):
    if doc.docstatus != 0:
        return

    company_currency = frappe.get_cached_value("Company", doc.company, "default_currency")
    bank_currency = doc.paid_from_account_currency or get_account_currency(doc.paid_from)
    party_currency = doc.paid_to_account_currency or get_account_currency(doc.paid_to)

    if not is_cross_payment(doc, bank_currency, party_currency, company_currency):
        if flt(doc.get("custom_bank_cross_rate")):
            doc.custom_bank_cross_rate = 0
        return

    cross_rate = flt(doc.custom_bank_cross_rate)
    if not cross_rate:
        frappe.throw(
            _("Enter the Bank Cross Rate from the bank advice: 1 {0} = ? {1}.").format(
                party_currency, bank_currency
            ),
            title=_("Bank Cross Rate Missing"),
        )

    received = flt(doc.received_amount)
    if not received:
        return

    bank_system_rate = flt(get_exchange_rate(bank_currency, company_currency, doc.posting_date))
    party_system_rate = flt(get_exchange_rate(party_currency, company_currency, doc.posting_date))
    validate_deviation(cross_rate, bank_system_rate, party_system_rate, bank_currency, party_currency)

    bank_rate = flt(doc.source_exchange_rate) or bank_system_rate
    doc.paid_amount = flt(received * cross_rate, doc.precision("paid_amount"))
    doc.source_exchange_rate = bank_rate
    base_paid = flt(doc.paid_amount * bank_rate, doc.precision("base_paid_amount"))
    doc.target_exchange_rate = flt(base_paid / received, doc.precision("target_exchange_rate"))


def is_cross_payment(doc, bank_currency, party_currency, company_currency):
    return (
        doc.payment_type == "Pay"
        and bank_currency
        and party_currency
        and bank_currency != party_currency
        and bank_currency != company_currency
        and party_currency != company_currency
    )


def get_account_currency(account):
    if not account:
        return None
    return frappe.get_cached_value("Account", account, "account_currency")


def validate_deviation(cross_rate, bank_system_rate, party_system_rate, bank_currency, party_currency):
    if not bank_system_rate or not party_system_rate:
        return

    system_cross_rate = party_system_rate / bank_system_rate
    deviation = abs(cross_rate / system_cross_rate - 1) * 100
    if deviation <= MAX_DEVIATION_PCT:
        return

    message = _("Bank Cross Rate {0} is {1}% off the system rate of 1 {2} = {3} {4}.").format(
        cross_rate, flt(deviation, 1), party_currency, flt(system_cross_rate, 6), bank_currency
    )
    if abs((1 / cross_rate) / system_cross_rate - 1) * 100 < deviation:
        message += " " + _("It may be the wrong way round. Try {0}.").format(flt(1 / cross_rate, 6))

    frappe.throw(message, title=_("Check Bank Cross Rate"))
