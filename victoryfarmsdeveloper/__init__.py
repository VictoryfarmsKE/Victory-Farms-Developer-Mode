__version__ = "0.0.1"

try:
    import frappe.twofactor
    from victoryfarmsdeveloper.victoryfarmsdeveloper.customization.twofactor import vf_send_token_via_sms
    frappe.twofactor.send_token_via_sms = vf_send_token_via_sms
except ImportError:
    pass

try:
    from victoryfarmsdeveloper.setup.financial_statement_totals import install as install_financial_statement_totals
    install_financial_statement_totals()
except Exception:
    pass
