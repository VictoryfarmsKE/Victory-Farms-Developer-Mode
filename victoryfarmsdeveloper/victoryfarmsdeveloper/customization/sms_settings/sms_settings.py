import frappe
from frappe import _, msgprint, throw
from frappe.utils import add_to_date, now_datetime, nowdate

MAX_ATTEMPTS = 3
STUCK_AFTER_MINUTES = 10
RETRY_AFTER_MINUTES = 5
REQUEST_TIMEOUT = (5, 20)


@frappe.whitelist()
def send_sms(receiver_list, msg, sender_name="", success_msg=True):
    import json

    if isinstance(receiver_list, str):
        receiver_list = json.loads(receiver_list)
        if not isinstance(receiver_list, list):
            receiver_list = [receiver_list]

    receiver_list = validate_receiver_nos(receiver_list)

    delivery = frappe.get_doc({
        "doctype": "SMS Delivery",
        "status": "Queued",
        "receivers": "\n".join(receiver_list),
        "message": frappe.safe_decode(msg),
    })
    delivery.insert(ignore_permissions=True)
    enqueue_delivery(delivery.name)


def enqueue_delivery(delivery_name):
    frappe.enqueue(
        "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.sms_settings.sms_settings.deliver_sms",
        queue="short" if getattr(frappe.local, "request", None) else "default",
        timeout=120,
        enqueue_after_commit=True,
        delivery_name=delivery_name,
    )


def deliver_sms(delivery_name):
    import requests

    delivery = frappe.get_doc("SMS Delivery", delivery_name)
    if delivery.status == "Sent":
        return

    delivery.db_set({"status": "Sending", "attempts": (delivery.attempts or 0) + 1})
    frappe.db.commit()

    receiver_list = delivery.receivers.split("\n")
    response = None

    try:
        ss = frappe.get_doc("SMS Settings", "SMS Settings")
        response = requests.post(
            ss.sms_gateway_url,
            json=build_request_body(ss, receiver_list, delivery.message),
            headers=get_headers(ss),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        error_message = f"Error sending SMS: {e}\nStatus Code: {response.status_code if response is not None else 'N/A'}\nResponse Text: {response.text if response is not None else 'N/A'}"
        delivery.db_set({"status": "Failed", "last_error": error_message[:1000]})
        frappe.db.commit()
        if delivery.attempts >= MAX_ATTEMPTS:
            frappe.log_error(title="SMS not delivered", message=f"SMS Delivery {delivery.name}\n{error_message}")
        return

    arg = {"receiver_list": receiver_list, "message": delivery.message.encode("utf-8")}
    sms_log = create_sms_log(arg, receiver_list)
    delivery.db_set({"status": "Sent", "sent_at": now_datetime(), "sms_log": sms_log, "last_error": None})
    frappe.db.commit()


def retry_failed_or_stuck_sms():
    stuck_before = add_to_date(now_datetime(), minutes=-STUCK_AFTER_MINUTES)
    retry_before = add_to_date(now_datetime(), minutes=-RETRY_AFTER_MINUTES)

    stuck = frappe.get_all(
        "SMS Delivery",
        filters={"status": ("in", ["Queued", "Sending"]), "modified": ("<", stuck_before)},
        fields=["name", "attempts"],
    )
    failed = frappe.get_all(
        "SMS Delivery",
        filters={"status": "Failed", "attempts": ("<", MAX_ATTEMPTS), "modified": ("<", retry_before)},
        fields=["name", "attempts"],
    )

    for row in stuck + failed:
        if (row.attempts or 0) >= MAX_ATTEMPTS:
            frappe.db.set_value("SMS Delivery", row.name, {"status": "Failed", "last_error": "Stuck: no delivery result after the last attempt"})
            frappe.log_error(title="SMS not delivered", message=f"SMS Delivery {row.name} stuck after {row.attempts} attempts")
            continue
        frappe.db.set_value("SMS Delivery", row.name, "status", "Queued")
        enqueue_delivery(row.name)

    frappe.db.commit()


def build_request_body(ss, receiver_list, message):
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

    return {
        "SenderId": sender_id,
        "MessageParameters": [{"Number": number, "Text": message} for number in receiver_list],
        "ApiKey": api_key,
        "ClientId": client_id
    }

def get_headers(self):
    headers = {"Accept": "text/plain, text/html, */*"}
    for d in self.get("parameters"):
        if d.header == 1:
            headers.update({d.parameter: d.value})
    return headers

def send_request(gateway_url, params, headers=None, use_post=True, use_json=True):
    import requests
    import json

    if headers is None:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # Fix request format
    formatted_params = {
        "SenderId": params.get("SenderId"),
        "MessageParameters": [
            {
                "Number": params.get("mobile"), 
                "Text": params.get("message")  
            }
        ],
        "ApiKey": params.get("ApiKey"),
        "ClientId": params.get("ClientId"),
    }

    kwargs = {"headers": headers, "json": formatted_params}

    try:
        response = requests.post(gateway_url, **kwargs)
        response.raise_for_status()
        return response.status_code

    except requests.exceptions.RequestException as e:
        error_details = {
            "URL": gateway_url,
            "Headers": headers,
            "Payload Sent": formatted_params,
            "Error": str(e),
        }

        frappe.log_error(title="SMS API Error", message=json.dumps(error_details, indent=2))
        return None

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
    return sl.name

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
