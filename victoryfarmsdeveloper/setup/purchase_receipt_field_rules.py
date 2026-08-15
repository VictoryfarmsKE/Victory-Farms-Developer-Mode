"""
Purchase Receipt field rules for Victory Farms.

Business rules enforced here:

1. Landed Costs is NEVER mandatory, for any value of `custom_type` or anything
   else. All reqd / mandatory_depends_on / custom_type-based depends_on rules on
   the landed cost fields are stripped.
2. Purchase Taxes and Charges Template (`taxes_and_charges`) is mandatory ONLY
   when `custom_type` is the Feeds option.

This module is wired to the `after_migrate` hook instead of `patches.txt` on
purpose. Patches are recorded in `tabPatch Log` and never run again, while
`sync_customizations` of every other installed app deletes and re-inserts ALL
Custom Fields and Property Setters of a DocType on every single migrate. Only an
`after_migrate` hook is guaranteed to run last, on every migrate.
"""

import frappe

DOCTYPE = "Purchase Receipt"
TYPE_FIELD = "custom_type"
TAX_TEMPLATE_FIELD = "taxes_and_charges"
TAX_FIELDS = ("taxes_and_charges", "taxes_charges_section", "taxes")
LANDED_COST_FIELDS = ("landed_cost_voucher", "custom_landed_costs")
DEFAULT_FEEDS_VALUE = "Feeds"


def get_feeds_option():
	"""
	Resolve the real Feeds option of `custom_type` instead of hardcoding it.

	The field is owned by another app, so its label may be "Feed" or "Feeds".
	Hardcoding the wrong one makes the rule silently never fire.
	"""
	options = frappe.db.get_value(
		"Custom Field", {"dt": DOCTYPE, "fieldname": TYPE_FIELD}, "options"
	)

	if not options:
		try:
			field = frappe.get_meta(DOCTYPE).get_field(TYPE_FIELD)
			options = field.options if field else None
		except Exception:
			options = None

	for option in (options or "").split("\n"):
		option = option.strip()
		if option and "feed" in option.lower():
			return option

	return DEFAULT_FEEDS_VALUE


def get_mandatory_expression(feeds_option=None):
	feeds_option = feeds_option or get_feeds_option()
	return 'eval:doc.{0}=="{1}"'.format(TYPE_FIELD, feeds_option)


def enforce():
	"""Idempotent enforcement of the rules above. Safe to run any number of times."""
	feeds_option = get_feeds_option()

	_clear_landed_cost_property_setters()
	_clear_landed_cost_custom_fields()
	_clear_foreign_feeds_mandatory_rules()
	_ensure_tax_fields_visible()
	_apply_tax_template_rule(feeds_option)
	_disable_landed_cost_scripts()

	frappe.clear_cache(doctype=DOCTYPE)
	frappe.db.commit()

	print(
		"VictoryFarmsDeveloper: Purchase Receipt rules enforced "
		"(Landed Costs optional, taxes_and_charges mandatory for "
		"{0}='{1}')".format(TYPE_FIELD, feeds_option)
	)


def _clear_landed_cost_property_setters():
	frappe.db.delete(
		"Property Setter",
		{
			"doctype_or_field": "DocField",
			"doc_type": DOCTYPE,
			"field_name": ("in", list(LANDED_COST_FIELDS)),
			"property": ("in", ["reqd", "mandatory_depends_on", "hidden"]),
		},
	)

	field_placeholders = ", ".join("%s" for _ in LANDED_COST_FIELDS)
	frappe.db.sql(
		"""
		DELETE FROM `tabProperty Setter`
		WHERE doctype_or_field = 'DocField'
		  AND doc_type = %s
		  AND property = 'depends_on'
		  AND field_name IN ({0})
		  AND value LIKE %s
		""".format(field_placeholders),
		(DOCTYPE, *LANDED_COST_FIELDS, "%{0}%".format(TYPE_FIELD)),
	)


def _clear_landed_cost_custom_fields():
	"""
	Strip the rules straight off the Custom Field rows too, because another
	app's `custom/purchase_receipt.json` re-inserts them on every migrate.
	"""
	names = frappe.get_all(
		"Custom Field",
		filters={"dt": DOCTYPE, "fieldname": ("in", LANDED_COST_FIELDS)},
		pluck="name",
	)

	for name in names:
		frappe.db.set_value(
			"Custom Field",
			name,
			{"reqd": 0, "mandatory_depends_on": None, "depends_on": None},
			update_modified=False,
		)


def _clear_foreign_feeds_mandatory_rules():
	"""Remove any custom_type-driven mandatory rule from every field except the tax template."""
	frappe.db.sql(
		"""
		DELETE FROM `tabProperty Setter`
		WHERE doctype_or_field = 'DocField'
		  AND doc_type = %s
		  AND property = 'mandatory_depends_on'
		  AND field_name != %s
		  AND value LIKE %s
		""",
		(DOCTYPE, TAX_TEMPLATE_FIELD, "%{0}%".format(TYPE_FIELD)),
	)

	frappe.db.sql(
		"""
		UPDATE `tabCustom Field`
		SET mandatory_depends_on = NULL
		WHERE dt = %s
		  AND fieldname != %s
		  AND mandatory_depends_on LIKE %s
		""",
		(DOCTYPE, TAX_TEMPLATE_FIELD, "%{0}%".format(TYPE_FIELD)),
	)


def _ensure_tax_fields_visible():
	for field_name in TAX_FIELDS:
		_upsert_property_setter(field_name, "hidden", "0", "Check")


def _apply_tax_template_rule(feeds_option):
	expression = get_mandatory_expression(feeds_option)

	_upsert_property_setter(
		TAX_TEMPLATE_FIELD, "mandatory_depends_on", expression, "Text"
	)

	if frappe.db.exists("Custom Field", {"dt": DOCTYPE, "fieldname": TAX_TEMPLATE_FIELD}):
		frappe.db.set_value(
			"Custom Field",
			{"dt": DOCTYPE, "fieldname": TAX_TEMPLATE_FIELD},
			{"mandatory_depends_on": expression, "hidden": 0},
			update_modified=False,
		)


def _disable_landed_cost_scripts():
	"""
	Disable any Client Script that forces Landed Costs to be mandatory.

	Property Setters alone cannot beat a Client Script calling
	`set_df_property(..., 'reqd', 1)` or throwing on save.
	"""
	scripts = frappe.get_all(
		"Client Script",
		filters={"dt": DOCTYPE, "enabled": 1},
		fields=["name", "script"],
	)

	for script in scripts:
		body = (script.script or "").lower()
		if "landed" not in body:
			continue
		if not any(token in body for token in ("reqd", "mandatory", "throw", "msgprint")):
			continue

		frappe.db.set_value("Client Script", script.name, "enabled", 0, update_modified=False)
		print(
			"VictoryFarmsDeveloper: disabled Client Script '{0}' "
			"(forced Landed Costs to be mandatory)".format(script.name)
		)


def _upsert_property_setter(field_name, property_name, value, property_type):
	existing = frappe.db.get_value(
		"Property Setter",
		{
			"doctype_or_field": "DocField",
			"doc_type": DOCTYPE,
			"field_name": field_name,
			"property": property_name,
		},
		"name",
	)

	if existing:
		frappe.db.set_value("Property Setter", existing, "value", value, update_modified=False)
		return

	setter = frappe.new_doc("Property Setter")
	setter.doctype_or_field = "DocField"
	setter.doc_type = DOCTYPE
	setter.field_name = field_name
	setter.property = property_name
	setter.value = value
	setter.property_type = property_type
	setter.module = "VictoryFarmsDeveloper"
	setter.insert(ignore_permissions=True)


def validate_purchase_receipt(doc, method=None):
	"""
	Server-side guarantee of the same rules, hooked on Purchase Receipt validate.

	This is the layer that cannot be wiped by another app's customization sync:
	even if the Property Setter disappears, Feeds receipts still require a tax
	template, and Landed Costs stays optional.
	"""
	for fieldname in LANDED_COST_FIELDS:
		meta_field = doc.meta.get_field(fieldname)
		if meta_field and meta_field.reqd:
			meta_field.reqd = 0

	doc_type = (doc.get(TYPE_FIELD) or "").strip()
	if not doc_type or "feed" not in doc_type.lower():
		return

	if not doc.get(TAX_TEMPLATE_FIELD):
		frappe.throw(
			frappe._(
				"Purchase Taxes and Charges Template is mandatory when Type is {0}."
			).format(frappe.bold(doc_type)),
			title=frappe._("Missing Purchase Taxes and Charges Template"),
		)


@frappe.whitelist()
def report_state():
	"""
	Diagnostic helper: `bench --site <site> execute
	victoryfarmsdeveloper.setup.purchase_receipt_field_rules.report_state`
	"""
	state = {
		"resolved_feeds_option": get_feeds_option(),
		"expected_expression": get_mandatory_expression(),
		"property_setters": frappe.get_all(
			"Property Setter",
			filters={
				"doc_type": DOCTYPE,
				"field_name": ("in", TAX_FIELDS + LANDED_COST_FIELDS),
			},
			fields=["field_name", "property", "value"],
		),
		"custom_fields": frappe.get_all(
			"Custom Field",
			filters={
				"dt": DOCTYPE,
				"fieldname": ("in", (TYPE_FIELD,) + TAX_FIELDS + LANDED_COST_FIELDS),
			},
			fields=["fieldname", "reqd", "depends_on", "mandatory_depends_on", "options"],
		),
		"client_scripts": frappe.get_all(
			"Client Script", filters={"dt": DOCTYPE}, fields=["name", "enabled"]
		),
	}

	print(frappe.as_json(state))
	return state
