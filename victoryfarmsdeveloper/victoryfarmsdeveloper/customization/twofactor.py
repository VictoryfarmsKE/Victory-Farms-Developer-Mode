import pyotp
import frappe
from frappe.utils.background_jobs import enqueue

def vf_send_token_via_sms(otpsecret, token=None, phone_no=None):
    """Custom implementation of send_token_via_sms"""
    try:
        from victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings import send_request
    except Exception as e:
        frappe.log_error(f"Error importing send_request: {str(e)}", "Custom 2FA")
        return False

    if not phone_no:
        frappe.log_error("Phone number missing in 2FA SMS", "Custom 2FA")
        return False

    # Ensure phone number is in international format
    if phone_no.startswith("0"):  # Assuming local number starts with '0'
        phone_no = "+254" + phone_no[1:]  # Replace leading '0' with '+254'

    ss = frappe.get_doc("SMS Settings", "SMS Settings")
    if not ss.sms_gateway_url:
        frappe.log_error("SMS Gateway URL missing", "Custom 2FA")
        return False

    hotp = pyotp.HOTP(otpsecret)
    args = {ss.message_parameter: f"Your verification code is {hotp.at(int(token))}"}

    for d in ss.get("parameters"):
        args[d.parameter] = d.value

    args[ss.receiver_parameter] = phone_no

    sms_args = {"params": args, "gateway_url": ss.sms_gateway_url, "use_post": ss.use_post}
    enqueue(
        method=send_request,
        queue="short",
        timeout=300,
        event=None,
        is_async=True,
        job_name=None,
        now=False,
        **sms_args,
    )
    return True