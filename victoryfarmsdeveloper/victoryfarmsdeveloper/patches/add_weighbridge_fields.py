import frappe

TARGET_DOCTYPE = "Stock Entry"
MODULE = "VictoryFarmsDeveloper"
ROLE = "Weighbridge Operator"
SETTINGS_DOCTYPE = "Weighbridge Settings"
PREFERRED_ANCHOR = "custom_calibration_scale"
FALLBACK_ANCHOR = "posting_time"

FIELDS = (
	{
		"fieldname": "custom_weighbridge_section",
		"fieldtype": "Section Break",
		"label": "Weighbridge",
		"collapsible": 1,
	},
	{
		"fieldname": "custom_weighbridge_tare_ref",
		"fieldtype": "Link",
		"label": "Empty Weight Reading",
		"options": "Weighbridge Reading",
		"read_only": 1,
	},
	{
		"fieldname": "custom_weighbridge_gross_ref",
		"fieldtype": "Link",
		"label": "Loaded Weight Reading",
		"options": "Weighbridge Reading",
		"read_only": 1,
	},
	{
		"fieldname": "custom_weighbridge_column",
		"fieldtype": "Column Break",
	},
	{
		"fieldname": "custom_weighbridge_expected_kg",
		"fieldtype": "Float",
		"label": "Expected Load (Kg)",
		"precision": "3",
		"read_only": 1,
	},
	{
		"fieldname": "custom_weighbridge_actual_kg",
		"fieldtype": "Float",
		"label": "Actual Load (Kg)",
		"precision": "3",
		"read_only": 1,
	},
	{
		"fieldname": "custom_weighbridge_variance_kg",
		"fieldtype": "Float",
		"label": "Variance (Kg)",
		"precision": "3",
		"read_only": 1,
	},
	{
		"fieldname": "custom_weighbridge_variance_pct",
		"fieldtype": "Float",
		"label": "Variance (%)",
		"precision": "2",
		"read_only": 1,
	},
)

DEFAULTS = {
	"enabled": 1,
	"enforce": 0,
	"tolerance_pct": 2.0,
	"tolerance_floor_kg": 25.0,
	"max_window_hours": 24,
}


def execute():
	_ensure_role()
	_ensure_fields()
	_seed_settings()

	frappe.db.commit()
	frappe.clear_cache(doctype=TARGET_DOCTYPE)


def _ensure_role():
	if frappe.db.exists("Role", ROLE):
		return

	role = frappe.new_doc("Role")
	role.role_name = ROLE
	role.desk_access = 1
	role.insert(ignore_permissions=True)


def _get_anchor():
	if frappe.db.exists("Custom Field", "{0}-{1}".format(TARGET_DOCTYPE, PREFERRED_ANCHOR)):
		return PREFERRED_ANCHOR

	return FALLBACK_ANCHOR


def _ensure_fields():
	anchor = _get_anchor()

	for spec in FIELDS:
		name = "{0}-{1}".format(TARGET_DOCTYPE, spec["fieldname"])

		if frappe.db.exists("Custom Field", name):
			cf = frappe.get_doc("Custom Field", name)
		else:
			cf = frappe.new_doc("Custom Field")
			cf.name = name
			cf.dt = TARGET_DOCTYPE
			cf.fieldname = spec["fieldname"]

		cf.fieldtype = spec["fieldtype"]
		cf.label = spec.get("label")
		cf.options = spec.get("options")
		cf.precision = spec.get("precision")
		cf.read_only = spec.get("read_only", 0)
		cf.collapsible = spec.get("collapsible", 0)
		cf.insert_after = anchor
		cf.module = MODULE
		cf.no_copy = 1
		cf.print_hide = 1
		cf.save(ignore_permissions=True)

		anchor = spec["fieldname"]


def _seed_settings():
	if frappe.db.exists("Singles", {"doctype": SETTINGS_DOCTYPE, "field": "enabled"}):
		return

	settings = frappe.get_single(SETTINGS_DOCTYPE)

	for fieldname, value in DEFAULTS.items():
		settings.set(fieldname, value)

	settings.save(ignore_permissions=True)
