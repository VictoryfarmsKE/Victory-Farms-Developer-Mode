import json
import re
from urllib.parse import unquote, urlparse

import frappe
from frappe.desk.search import build_for_autosuggest, get_std_fields_list
from frappe.desk.search import search_link as frappe_search_link

TILL_PAGES = ("point-of-sale", "pos-payments")
WORD_INDEX = "ft_customer_name"
CANDIDATE_LIMIT = 50
POPULAR_FIRST_FROM_LENGTH = 3
SETTINGS_CACHE_KEY = "vf_till_customer_search_settings"
SETTINGS_CACHE_SECONDS = 600
OVERRIDDEN_METHOD = "frappe.desk.search.search_link"
OVERRIDE_METHOD = "victoryfarmsdeveloper.setup.till_customer_search.search_link"
UPSTREAM_MARKERS = (
	("frappe", ("public", "js", "frappe", "form", "controls", "link.js"), '"frappe.desk.search.search_link"'),
	("erpnext", ("selling", "page", "point_of_sale", "pos_item_cart.js"), 'options: "Customer"'),
	("erpnext", ("selling", "page", "point_of_sale", "pos_item_cart.js"), "make_customer_selector() {"),
	("erpnext", ("selling", "page", "point_of_sale", "pos_item_cart.js"), "erpnext.PointOfSale.ItemCart = class"),
	("frappe", ("public", "js", "frappe", "router.js"), 'return name.toLowerCase().replace(/ /g, "-");'),
)


@frappe.whitelist()
def search_link(
	doctype,
	txt,
	query=None,
	filters=None,
	page_length=10,
	searchfield=None,
	reference_doctype=None,
	ignore_user_permissions=False,
):
	text = (txt or "").strip()
	if doctype != "Customer" or query or searchfield or not text or not is_till_request():
		return frappe_search_link(
			doctype,
			txt,
			query=query,
			filters=filters,
			page_length=page_length,
			searchfield=searchfield,
			reference_doctype=reference_doctype,
			ignore_user_permissions=ignore_user_permissions,
		)

	candidates = find_candidates(text)
	if not candidates:
		return []

	meta = frappe.get_meta("Customer")
	fields = [f"`tabCustomer`.`{f}`" for f in get_std_fields_list(meta, "name")]
	values = frappe.get_list(
		"Customer",
		filters=customer_filters(filters) + [["Customer", "name", "in", candidates]],
		fields=fields,
		order_by="`tabCustomer`.idx desc",
		limit_page_length=frappe.utils.cint(page_length) or 10,
		reference_doctype=reference_doctype,
		as_list=True,
		strict=False,
	)
	return build_for_autosuggest(values, doctype="Customer")


def is_till_request():
	referrer = frappe.get_request_header("Referer") or ""
	parts = [part for part in unquote(urlparse(referrer).path).split("/") if part]
	return len(parts) >= 2 and parts[0] == "app" and parts[1] in TILL_PAGES


def customer_filters(filters):
	if isinstance(filters, str):
		filters = json.loads(filters) if filters else []
	if isinstance(filters, dict):
		filters = [["Customer", key, *(value if isinstance(value, list) else ["=", value])] for key, value in filters.items()]
	return list(filters or []) + [["Customer", "disabled", "!=", 1]]


def find_candidates(text):
	if is_phone(text):
		return phone_candidates(re.sub(r"\D", "", text))
	return name_candidates(text)


def is_phone(text):
	compact = re.sub(r"[\s+\-()]", "", text)
	return bool(compact) and compact.isdigit()


def phone_candidates(digits):
	local = digits[1:] if digits.startswith("0") else digits[3:] if digits.startswith("254") else digits
	patterns = [f"0{local}%", f"254{local}%", f"+254{local}%", f"{local}%"] if local else [f"{digits}%"]
	names = []
	for pattern in patterns:
		names += frappe.db.sql(
			f"""select name from `tabCustomer` where mobile_no like %s and disabled = 0
			{popular_first(digits)} limit {CANDIDATE_LIMIT}""",
			(pattern,),
			pluck=True,
		)
	return unique(names)[:CANDIDATE_LIMIT]


def name_candidates(text):
	words = [w for w in (re.sub(r"[^0-9A-Za-z]", "", part) for part in text.split()) if w]
	searchable = [w for w in words if len(w) >= min_word_length() and w.lower() not in stopwords()]
	names = frappe.db.sql(
		f"""select name from `tabCustomer` where name like %s and disabled = 0 limit {CANDIDATE_LIMIT}""",
		(starts_with(text),),
		pluck=True,
	)
	if searchable and has_word_index():
		against = " ".join(f"+{w}*" for w in searchable)
		names += frappe.db.sql(
			f"""select name from `tabCustomer`
			where match(customer_name) against (%s in boolean mode) and disabled = 0
			{popular_first(text)} limit {CANDIDATE_LIMIT}""",
			(against,),
			pluck=True,
		)
	else:
		names += frappe.db.sql(
			f"""select name from `tabCustomer` where customer_name like %s and disabled = 0
			{popular_first(text)} limit {CANDIDATE_LIMIT}""",
			(starts_with(text),),
			pluck=True,
		)
	return unique(names)[:CANDIDATE_LIMIT]


def popular_first(text):
	return "order by idx desc" if len(text) >= POPULAR_FIRST_FROM_LENGTH else ""


def unique(values):
	return list(dict.fromkeys(values))


def starts_with(text):
	return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def has_word_index():
	return search_settings()["word_index"]


def min_word_length():
	return search_settings()["min_word_length"]


def stopwords():
	return set(search_settings()["stopwords"])


def search_settings():
	settings = frappe.cache.get_value(SETTINGS_CACHE_KEY)
	if settings is None:
		enabled, min_length = frappe.db.sql("select @@innodb_ft_enable_stopword, @@innodb_ft_min_token_size")[0]
		settings = {
			"word_index": bool(frappe.db.has_index("tabCustomer", WORD_INDEX)),
			"min_word_length": frappe.utils.cint(min_length) or 3,
			"stopwords": frappe.db.sql(
				"select value from information_schema.INNODB_FT_DEFAULT_STOPWORD", pluck=True
			)
			if frappe.utils.cint(enabled)
			else [],
		}
		frappe.cache.set_value(SETTINGS_CACHE_KEY, settings, expires_in_sec=SETTINGS_CACHE_SECONDS)
	return settings


def check():
	problems = [
		f"{app}/{'/'.join(path)} no longer contains {marker}"
		for app, path, marker in UPSTREAM_MARKERS
		if marker not in read_app_file(app, path)
	]
	active = frappe.override_whitelisted_method(OVERRIDDEN_METHOD)
	if active != OVERRIDE_METHOD:
		problems.append(f"{OVERRIDDEN_METHOD} resolves to {active}, not {OVERRIDE_METHOD}")
	frappe.cache.delete_value(SETTINGS_CACHE_KEY)
	if not has_word_index():
		problems.append(f"tabCustomer has no {WORD_INDEX} index, till name search falls back to starts-with")
	if problems:
		frappe.log_error(title="Till customer search check failed", message="\n".join(problems))
	return problems


def read_app_file(app, path):
	try:
		with open(frappe.get_app_path(app, *path)) as f:
			return f.read()
	except OSError:
		return ""
