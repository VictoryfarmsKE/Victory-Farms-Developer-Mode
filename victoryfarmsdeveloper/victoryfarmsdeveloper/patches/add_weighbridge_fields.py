import frappe

ROLE = "Weighbridge Operator"
SETTINGS_DOCTYPE = "Weighbridge Settings"

DEFAULTS = {
	"enabled": 1,
	"enforce": 0,
	"tolerance_pct": 2.0,
	"tolerance_floor_kg": 25.0,
	"max_window_hours": 24,
}


def execute():
	_ensure_role()
	_seed_settings()

	frappe.db.commit()


def _ensure_role():
	if frappe.db.exists("Role", ROLE):
		return

	role = frappe.new_doc("Role")
	role.role_name = ROLE
	role.desk_access = 1
	role.insert(ignore_permissions=True)


def _seed_settings():
	if frappe.db.exists("Singles", {"doctype": SETTINGS_DOCTYPE, "field": "enabled"}):
		return

	settings = frappe.get_single(SETTINGS_DOCTYPE)

	for fieldname, value in DEFAULTS.items():
		settings.set(fieldname, value)

	settings.save(ignore_permissions=True)
