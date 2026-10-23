import frappe
from frappe import _, msgprint, throw
from frappe.utils import add_to_date, now_datetime, nowdate

MAX_ATTEMPTS = 3
STUCK_AFTER_MINUTES = 10
RETRY_AFTER_MINUTES = 5
RETRY_BATCH_SIZE = 200
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
        queue="default",
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
        order_by="modified asc",
        limit=RETRY_BATCH_SIZE,
    )
    failed = frappe.get_all(
        "SMS Delivery",
        filters={"status": "Failed", "attempts": ("<", MAX_ATTEMPTS), "modified": ("<", retry_before)},
        fields=["name", "attempts"],
        order_by="modified asc",
        limit=RETRY_BATCH_SIZE - len(stuck),
    ) if len(stuck) < RETRY_BATCH_SIZE else []

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


# ---------------------------------------------------------------------------
# Daily consolidated egg-collection SMS
# ---------------------------------------------------------------------------

EGG_PRICE_PER_KG = 1200  # KES, fixed for all partners
HAPA_AREA_SQM = 80  # m2 per hapa net

# Pond -> number of hapas (source: Pond Flipping Schedule)
# Used as fallback when the Pond DocType has no matching record.
HAPA_COUNTS = {
    "B11": 15,
    "H1-02": 15,
    "B8": 16,
    "H0-07": 18,
    "H2-07": 4,
    "H2-04": 10,
    "H2-06": 9,
    "H0-10": 17,
}


def get_hapa_counts():
    """Return pond -> hapa_count mapping.

    Reads from the **Pond** DocType first; falls back to the hardcoded
    HAPA_COUNTS dict for any pond not found in the DocType.
    """
    counts = dict(HAPA_COUNTS)  # start with fallback
    try:
        for row in frappe.get_all("Pond", fields=["pond_name", "number_of_hapas"]):
            if row.pond_name and row.number_of_hapas:
                counts[row.pond_name] = int(row.number_of_hapas)
    except Exception:
        pass  # Pond DocType may not exist yet (pre-migration)
    return counts


def _format_mobile(raw):
    """Normalise a Kenyan mobile number to 254XXXXXXXXX format."""
    if not raw:
        return None
    cleaned = raw.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if cleaned.startswith("0"):
        return "254" + cleaned[1:]
    if cleaned.startswith("+254"):
        return cleaned[1:]
    if cleaned.startswith("254"):
        return cleaned
    return cleaned


@frappe.whitelist()
def send_daily_egg_collection_summary():
    """Scheduled at 18:00 daily.

    Queries every submitted "Egg collection" Project Update for today,
    groups them by client and sends **one** consolidated SMS per client.
    Works the same whether the partner has 1 pond or 10.
    """
    today = nowdate()

    records = frappe.db.sql(
        """
        SELECT custom_client,
               custom_client_mobile,
               custom_pond,
               custom_number_of_eggs_collected,
               custom_additional_notes,
               custom_project_name,
               date
        FROM `tabProject Update`
        WHERE custom_activity = 'Egg collection'
          AND docstatus = 1
          AND date = %s
          AND custom_client IS NOT NULL
          AND custom_client != ''
        """,
        today,
        as_dict=True,
    )

    if not records:
        frappe.log_error(
            "No egg-collection records for " + today, "Daily SMS Summary"
        )
        return "No egg-collection records for " + today

    # ---- group by client --------------------------------------------------
    clients = {}
    for r in records:
        client = r.custom_client
        if client not in clients:
            clients[client] = {
                "mobile": r.custom_client_mobile,
                "ponds": [],
                "total_eggs": 0.0,
                "project": r.custom_project_name or "Victory Farm Project",
                "date": r.date,
            }
        eggs = float(r.custom_number_of_eggs_collected or 0)
        clients[client]["ponds"].append(
            {"pond": r.custom_pond or "N/A", "eggs": eggs}
        )
        clients[client]["total_eggs"] += eggs

    # ---- MTD / YTD helper -------------------------------------------------
    def _sum_eggs(client_name, from_date):
        result = frappe.db.sql(
            """
            SELECT SUM(custom_number_of_eggs_collected)
            FROM `tabProject Update`
            WHERE custom_client = %s
              AND custom_activity = 'Egg collection'
              AND docstatus = 1
              AND date >= %s
            """,
            (client_name, from_date),
        )
        return float(result[0][0] or 0)

    month_start = frappe.utils.get_first_day(today)
    year_start = frappe.utils.get_year_start(today)

    # ---- build & send one message per client ------------------------------
    hapa_map = get_hapa_counts()
    sent = []
    failed = []

    for client_name, data in clients.items():
        mobile = _format_mobile(data["mobile"])
        if not mobile:
            failed.append(client_name + " (no mobile)")
            continue

        total_eggs = data["total_eggs"]
        earnings = total_eggs * EGG_PRICE_PER_KG

        # Hapa efficiency (only meaningful when ponds are in the map)
        efficiencies = []
        for pd_ in data["ponds"]:
            nh = hapa_map.get(pd_["pond"], 0)
            if nh > 0:
                efficiencies.append(pd_["eggs"] / (nh * HAPA_AREA_SQM))
        avg_efficiency = (
            round(sum(efficiencies) / len(efficiencies), 2)
            if efficiencies
            else None
        )

        mtd_eggs = _sum_eggs(client_name, month_start)
        ytd_eggs = _sum_eggs(client_name, year_start)

        # ---- compose message ----
        msg = (
            "Hello "
            + client_name
            + ", thank you for being a valued Victory Pond Partner."
            + " We are dedicated to growing together.\n\n"
        )
        msg += (
            "Today's collections ("
            + frappe.utils.format_date(data["date"])
            + "):\n\n"
        )

        for pd_ in data["ponds"]:
            msg += (
                "Pond " + pd_["pond"] + ": "
                + str(round(pd_["eggs"], 3)) + " Kg\n"
            )

        msg += (
            "\nTotal collected today: " + str(round(total_eggs, 2)) + " Kg\n"
        )
        msg += "Earning you: KES " + str(round(earnings, 2)) + "\n"

        if avg_efficiency is not None:
            msg += (
                "Hapa Efficiency (avg): "
                + str(avg_efficiency)
                + " g/m2\n"
            )

        msg += (
            "\nMonth to date: " + str(round(mtd_eggs, 2)) + " kg eggs\n"
        )
        msg += "Year to date: " + str(round(ytd_eggs, 2)) + " kg eggs\n\n"

        msg += (
            "Your partnership is important to both our development."
            " We welcome you to join the harvesting for Verification"
            " and transparency of the process.\n\n"
        )
        msg += (
            "Thank you again for partnering with us in feeding"
            " families with Fresh Kenyan Tilapia."
        )

        # ---- send ----
        try:
            send_sms(receiver_list=[mobile], msg=msg)
            sent.append(client_name)
        except Exception as e:
            frappe.log_error(
                "Daily summary SMS failed for "
                + client_name
                + ": "
                + str(e),
                "Daily SMS Error",
            )
            failed.append(client_name)

    summary = (
        "Daily egg SMS summary for "
        + today
        + ". Sent: "
        + str(len(sent))
        + ". Failed: "
        + str(len(failed))
    )
    frappe.log_error(summary, "Daily SMS Summary")
    return summary
