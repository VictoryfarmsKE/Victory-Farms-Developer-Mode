import frappe
from frappe import _, msgprint, throw
from frappe.utils import nowdate

@frappe.whitelist()
def send_sms(receiver_list, msg, sender_name="", success_msg=True):
    import json

    if isinstance(receiver_list, str):
        receiver_list = json.loads(receiver_list)
        if not isinstance(receiver_list, list):
            receiver_list = [receiver_list]

    receiver_list = validate_receiver_nos(receiver_list)

    arg = {
        "receiver_list": receiver_list,
        "message": frappe.safe_decode(msg).encode("utf-8"),
        "success_msg": success_msg,
    }

    import requests
    ss = frappe.get_doc("SMS Settings", "SMS Settings")
    headers = get_headers(ss)

    # Retrieve parameters from SMS settings
    sender_id = None
    api_key = None
    client_id = None
    for param in ss.get("parameters"):
        if param.parameter == "SenderId":
            sender_id = param.value
        elif param.parameter == "ApiKey":
            api_key = param.value
        elif param.parameter == "ClientId":
            client_id = param.value

    # Construct the request body
    request_body = {
        "SenderId": sender_id,
        "MessageParameters": [{"Number": number, "Text": frappe.safe_decode(arg.get("message"))} for number in arg.get("receiver_list")],
        "ApiKey": api_key,
        "ClientId": client_id
    }

    try:
        response = requests.post(ss.sms_gateway_url, json=request_body, headers=headers)
        response.raise_for_status()
        create_sms_log(arg, arg.get("receiver_list"))
        frappe.msgprint(_("SMS sent successfully"))

    except requests.exceptions.RequestException as e:
        error_message = f"Error sending SMS: {e}\nStatus Code: {response.status_code if response else 'N/A'}\nResponse Text: {response.text if response else 'N/A'}"
        frappe.log_error(f"Error sending SMS: {error_message}")
        frappe.msgprint(f"Error sending SMS: {error_message}")

def get_headers(self):
    headers = {"Accept": "text/plain, text/html, */*"}
    for d in self.get("parameters"):
        if d.header == 1:
            headers.update({d.parameter: d.value})
    return headers

def send_request(self, gateway_url, params, headers=None, use_post=False, use_json=False):
    import requests

    if not headers:
        headers = self.get_headers()
    kwargs = {"headers": headers}

    if use_json:
        kwargs["json"] = params
    elif use_post:
        kwargs["data"] = params
    else:
        kwargs["params"] = params

    if use_post:
        response = requests.post(gateway_url, **kwargs)
    else:
        response = requests.get(gateway_url, **kwargs)
    response.raise_for_status()
    return response.status_code

def create_sms_log(args, sent_to):
    sl = frappe.new_doc("SMS Log")
    sl.sent_on = nowdate()
    sl.message = args["message"].decode("utf-8")
    sl.no_of_requested_sms = len(args["receiver_list"])
    sl.requested_numbers = "\n".join(args["receiver_list"])
    sl.no_of_sent_sms = len(sent_to)
    sl.sent_to = "\n".join(sent_to)
    sl.flags.ignore_permissions = True
    sl.save()

def validate_receiver_nos(receiver_list):
    validated_receiver_list = []
    for d in receiver_list:
        if not d:
            continue

        # remove invalid character
        for x in [" ", "-", "(", ")"]:
            d = d.replace(x, "")

        validated_receiver_list.append(d)

    if not validated_receiver_list:
        throw(_("Please enter valid mobile nos"))

    return validated_receiver_list
