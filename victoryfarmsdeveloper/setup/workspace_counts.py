from urllib.parse import unquote, urlparse

import frappe
from frappe.desk.reportview import get_count as frappe_get_count

WORKSPACE_COUNT_LIMIT = 1001
WORKSPACE_SLUGS_CACHE_KEY = "vf_workspace_slugs"
WORKSPACE_SLUGS_CACHE_SECONDS = 600
OVERRIDDEN_METHOD = "frappe.desk.reportview.get_count"
OVERRIDE_METHOD = "victoryfarmsdeveloper.setup.workspace_counts.get_count"
FRAPPE_COUNT_PATHS = (
	(("public", "js", "frappe", "db.js"), '"frappe.desk.reportview.get_count"'),
	(("public", "js", "frappe", "widgets", "shortcut_widget.js"), ".count(this.link_to"),
	(("public", "js", "frappe", "list", "list_view.js"), "limit: this.count_upper_bound"),
	(("public", "js", "frappe", "router.js"), 'return name.toLowerCase().replace(/ /g, "-");'),
)


@frappe.whitelist()
def get_count():
	if frappe.form_dict.get("limit") in (None, "") and is_workspace_request():
		frappe.form_dict.limit = WORKSPACE_COUNT_LIMIT
	return frappe_get_count()


def is_workspace_request():
	referrer = frappe.get_request_header("Referer") or ""
	parts = [part for part in unquote(urlparse(referrer).path).split("/") if part]
	if not parts or parts[0] != "app":
		return False
	if len(parts) == 1:
		return True
	if len(parts) == 3 and parts[1] == "private":
		return parts[2] in workspace_slugs()
	return len(parts) == 2 and parts[1] in workspace_slugs()


def workspace_slugs():
	slugs = frappe.cache.get_value(WORKSPACE_SLUGS_CACHE_KEY)
	if slugs is None:
		slugs = sorted(
			{
				slug(value)
				for row in frappe.get_all("Workspace", fields=["name", "title"])
				for value in (row.name, row.title)
				if value
			}
		)
		frappe.cache.set_value(WORKSPACE_SLUGS_CACHE_KEY, slugs, expires_in_sec=WORKSPACE_SLUGS_CACHE_SECONDS)
	return slugs


def slug(name):
	return name.lower().replace(" ", "-")


def check():
	problems = [
		f"frappe/{'/'.join(path)} no longer contains {marker}"
		for path, marker in FRAPPE_COUNT_PATHS
		if marker not in read_frappe_file(path)
	]
	active = frappe.override_whitelisted_method(OVERRIDDEN_METHOD)
	if active != OVERRIDE_METHOD:
		problems.append(f"{OVERRIDDEN_METHOD} resolves to {active}, not {OVERRIDE_METHOD}")
	if problems:
		frappe.log_error(title="Workspace count cap check failed", message="\n".join(problems))
	return problems


def read_frappe_file(path):
	try:
		with open(frappe.get_app_path("frappe", *path)) as f:
			return f.read()
	except OSError:
		return ""
