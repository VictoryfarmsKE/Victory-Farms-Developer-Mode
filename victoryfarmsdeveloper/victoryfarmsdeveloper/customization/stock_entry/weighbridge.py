import frappe
from frappe import _
from frappe.utils import flt, get_datetime

TRANSIT_WAREHOUSE_TYPE = "Transit"
SETTINGS_DOCTYPE = "Weighbridge Settings"

KG_PER_UOM = {
	"Kg": 1.0,
	"Kilograms": 1.0,
	"Kilogram": 1.0,
	"Grams": 0.001,
	"Gram": 0.001,
}

VARIANCE_KG_FIELD = "custom_weighbridge_variance_kg"
VARIANCE_PCT_FIELD = "custom_weighbridge_variance_pct"
TARE_REF_FIELD = "custom_weighbridge_tare_ref"
GROSS_REF_FIELD = "custom_weighbridge_gross_ref"
EXPECTED_FIELD = "custom_weighbridge_expected_kg"
ACTUAL_FIELD = "custom_weighbridge_actual_kg"


def check_weighbridge(doc):
	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)

	if not settings.enabled:
		return

	truck = get_truck(doc)

	if not truck:
		return

	readings = get_visit_readings(truck, doc.creation, settings)

	if not readings:
		return

	tare, gross = readings
	entries = get_visit_entries(truck, tare.reading_time, gross.reading_time)
	expected, unpriced = get_expected_weight(entries, truck, settings)

	if unpriced:
		record_unpriced(doc, truck, unpriced)
		return

	actual = flt(gross.weight) - flt(tare.weight)
	variance = actual - expected
	tolerance = get_tolerance(expected, settings)
	variance_pct = (variance / expected * 100.0) if expected else 0.0

	store_result(doc, tare, gross, expected, actual, variance, variance_pct)

	if abs(variance) <= tolerance:
		return

	if not settings.enforce:
		return

	frappe.throw(
		_(
			"Weighbridge check failed for {truck}.<br><br>"
			"Empty weight ({tare_name}): <b>{tare:,.1f} kg</b><br>"
			"Loaded weight ({gross_name}): <b>{gross:,.1f} kg</b><br>"
			"Actually loaded: <b>{actual:,.1f} kg</b><br>"
			"Expected from {count} dispatch(es): <b>{expected:,.1f} kg</b><br>"
			"Difference: <b>{variance:+,.1f} kg</b> ({variance_pct:+.1f}%), "
			"allowed {tolerance:,.1f} kg."
		).format(
			truck=truck,
			tare_name=tare.name,
			tare=flt(tare.weight),
			gross_name=gross.name,
			gross=flt(gross.weight),
			actual=actual,
			count=len(entries),
			expected=expected,
			variance=variance,
			variance_pct=variance_pct,
			tolerance=tolerance,
		),
		title=_("Weighbridge Variance"),
	)


def get_truck(doc):
	targets = {row.t_warehouse for row in (doc.items or []) if row.t_warehouse}

	if not targets:
		return None

	trucks = frappe.get_all(
		"Warehouse",
		filters={"name": ("in", list(targets)), "warehouse_type": TRANSIT_WAREHOUSE_TYPE},
		pluck="name",
	)

	return trucks[0] if len(trucks) == 1 else None


def get_visit_readings(truck, reference_time, settings):
	window = frappe.utils.cint(settings.max_window_hours) or 24

	tare = frappe.get_all(
		"Weighbridge Reading",
		filters={
			"truck": truck,
			"reading_type": "Tare",
			"docstatus": 1,
			"reading_time": ("<=", reference_time),
		},
		fields=["name", "weight", "reading_time"],
		order_by="reading_time desc",
		limit=1,
	)

	if not tare:
		return None

	gross = frappe.get_all(
		"Weighbridge Reading",
		filters={
			"truck": truck,
			"reading_type": "Gross",
			"docstatus": 1,
			"reading_time": (">=", reference_time),
		},
		fields=["name", "weight", "reading_time"],
		order_by="reading_time asc",
		limit=1,
	)

	if not gross:
		return None

	tare, gross = tare[0], gross[0]
	span = get_datetime(gross.reading_time) - get_datetime(tare.reading_time)

	if span.total_seconds() > window * 3600:
		return None

	return tare, gross


def get_visit_entries(truck, tare_time, gross_time):
	return frappe.db.sql(
		"""
		select distinct se.name
		from `tabStock Entry` se
		inner join `tabStock Entry Detail` sed on sed.parent = se.name
		where sed.t_warehouse = %(truck)s
			and se.docstatus < 2
			and se.creation between %(tare_time)s and %(gross_time)s
		""",
		{"truck": truck, "tare_time": tare_time, "gross_time": gross_time},
		pluck="name",
	)


def get_expected_weight(entries, truck, settings):
	if not entries:
		return 0.0, []

	rows = frappe.db.sql(
		"""
		select sed.item_code, sed.stock_uom, sum(sed.transfer_qty) as qty, i.item_group
		from `tabStock Entry Detail` sed
		inner join `tabItem` i on i.name = sed.item_code
		where sed.parent in %(entries)s
			and sed.t_warehouse = %(truck)s
		group by sed.item_code, sed.stock_uom, i.item_group
		""",
		{"entries": entries, "truck": truck},
		as_dict=True,
	)

	by_item, by_group = get_unit_weight_maps(settings)
	total = 0.0
	unpriced = []

	for row in rows:
		if row.stock_uom in KG_PER_UOM:
			unit_weight = KG_PER_UOM[row.stock_uom]
		elif row.item_code in by_item:
			unit_weight = by_item[row.item_code]
		elif row.item_group in by_group:
			unit_weight = by_group[row.item_group]
		else:
			unpriced.append(row.item_code)
			continue

		total += flt(row.qty) * flt(unit_weight)

	return total, unpriced


def get_unit_weight_maps(settings):
	by_item = {}
	by_group = {}

	for row in settings.unit_weights or []:
		if row.item_code:
			by_item[row.item_code] = flt(row.weight_kg)
		elif row.item_group:
			by_group[row.item_group] = flt(row.weight_kg)

	return by_item, by_group


def get_tolerance(expected, settings):
	return max(
		abs(flt(expected)) * flt(settings.tolerance_pct) / 100.0,
		flt(settings.tolerance_floor_kg),
	)


def store_result(doc, tare, gross, expected, actual, variance, variance_pct):
	values = {
		TARE_REF_FIELD: tare.name,
		GROSS_REF_FIELD: gross.name,
		EXPECTED_FIELD: expected,
		ACTUAL_FIELD: actual,
		VARIANCE_KG_FIELD: variance,
		VARIANCE_PCT_FIELD: variance_pct,
	}

	meta = doc.meta

	for fieldname, value in values.items():
		if meta.has_field(fieldname):
			doc.set(fieldname, value)


def record_unpriced(doc, truck, unpriced):
	frappe.log_error(
		message=_(
			"Weighbridge check skipped for {0} on {1}. No unit weight configured for: {2}. "
			"Add them under Weighbridge Settings."
		).format(truck, doc.name, ", ".join(sorted(set(unpriced)))),
		title="Weighbridge: missing unit weights",
	)
