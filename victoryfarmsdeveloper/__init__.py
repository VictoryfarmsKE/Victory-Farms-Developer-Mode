__version__ = "0.0.1"

import frappe.twofactor
from victoryfarmsdeveloper.victoryfarmsdeveloper.customization.twofactor import vf_send_token_via_sms
frappe.twofactor.send_token_via_sms = vf_send_token_via_sms