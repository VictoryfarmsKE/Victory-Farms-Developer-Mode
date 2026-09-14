# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.utils import cint, flt, date_diff, getdate

# Matches PO-like tokens in free text, e.g. "PO 2400396", "PO-24-00801", "PO2400900"
PO_TOKEN_RE = re.compile(r"PO[\s\-]?\d[\d\s\-]*\d|PO\s*\d+", re.IGNORECASE)


def normalize_key(value):
	"""Strip everything but letters/digits and uppercase, so 'PO 2400396',
	'po-2400396' and 'PO2400396' all collapse to the same key."""
	return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def execute(filters=None):
	return AdvancesAgeing(filters).run()


class AdvancesAgeing:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.report_date = self.filters.report_date or frappe.utils.today()

	def run(self):
		if cint(self.filters.get("show_unmatched")):
			self.get_unmatched_columns()
			self.get_unmatched_data()
		else:
			self.get_columns()
			self.get_data()
		return self.columns, self.data

	def get_unmatched_columns(self):
		self.columns = [
			{
				"label": _("Payment Entry"),
				"fieldname": "payment_entry",
				"fieldtype": "Link",
				"options": "Payment Entry",
				"width": 150,
			},
			{"label": _("Reference No"), "fieldname": "reference_no", "fieldtype": "Data", "width": 350},
			{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
			{
				"label": _("Paid Amount"),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 130,
			},
			{
				"label": _("Allocated to Purchase Invoice"),
				"fieldname": "allocated_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 180,
			},
			{
				"label": _("Unallocated"),
				"fieldname": "unallocated",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 130,
			},
			{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
		]

	def get_unmatched_data(self):
		_matched, unmatched = self.get_raw_data()
		self.data = []
		for d in unmatched:
			unallocated = flt(d.paid_amount) - flt(d.allocated_total)
			if unallocated <= 0:
				continue
			d.unallocated = unallocated
			self.data.append(d)

	def get_columns(self):
		self.columns = [
			{
				"label": _("Supplier"),
				"fieldname": "supplier",
				"fieldtype": "Link",
				"options": "Supplier",
				"width": 150,
			},
			{
				"label": _("Supplier Name"),
				"fieldname": "supplier_name",
				"fieldtype": "Data",
				"width": 180,
			},
			{
				"label": _("Outstanding Advance"),
				"fieldname": "outstanding",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			},
			{
				"label": _("Withholding Tax"),
				"fieldname": "withholding_tax",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 130,
			},
			{"label": _("0-30"), "fieldname": "aged_0_30", "fieldtype": "Currency", "options": "currency", "width": 120},
			{"label": _("31-60"), "fieldname": "aged_31_60", "fieldtype": "Currency", "options": "currency", "width": 120},
			{"label": _("61-90"), "fieldname": "aged_61_90", "fieldtype": "Currency", "options": "currency", "width": 120},
			{"label": _("91-120"), "fieldname": "aged_91_120", "fieldtype": "Currency", "options": "currency", "width": 120},
			{
				"label": _("121 and above"),
				"fieldname": "aged_121_above",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 130,
			},
			{
				"label": _("Supplier Group"),
				"fieldname": "supplier_group",
				"fieldtype": "Link",
				"options": "Supplier Group",
				"width": 130,
			},
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Link",
				"options": "Currency",
				"width": 80,
			},
		]

	def get_po_lookup(self):
		"""normalized PO name -> supplier, for fuzzy-matching reference_no text."""
		po_rows = frappe.db.get_all("Purchase Order", fields=["name", "supplier"])
		lookup = {}
		for po in po_rows:
			lookup[normalize_key(po.name)] = po.supplier
		return lookup

	def get_supplier_meta(self):
		rows = frappe.db.get_all("Supplier", fields=["name", "supplier_name", "supplier_group"])
		return {r.name: r for r in rows}

	def match_supplier(self, reference_no, po_lookup):
		"""Extract PO-like tokens from free text reference_no and resolve to a
		supplier. Returns None if nothing matches, or if the text references
		more than one distinct supplier (ambiguous -> flagged, not guessed)."""
		if not reference_no:
			return None

		tokens = PO_TOKEN_RE.findall(reference_no)
		for part in reference_no.split("/"):
			tokens.extend(PO_TOKEN_RE.findall(part))

		matched_suppliers = set()
		for token in tokens:
			key = normalize_key(token)
			if key in po_lookup:
				matched_suppliers.add(po_lookup[key])

		if len(matched_suppliers) == 1:
			return matched_suppliers.pop()
		return None

	def get_raw_data(self):
		conditions = ""
		if self.filters.get("company"):
			conditions += " AND pe.company = %(company)s"

		pe_rows = frappe.db.sql(
			f"""
			SELECT
				pe.name AS payment_entry,
				pe.reference_no AS reference_no,
				pe.posting_date AS posting_date,
				pe.paid_amount AS paid_amount,
				pe.paid_from_account_currency AS currency,
				pe.custom_withholding_taxes AS withholding_tax
			FROM `tabPayment Entry` pe
			WHERE
				pe.docstatus = 1
				AND pe.payment_type = 'Internal Transfer'
				AND pe.posting_date <= %(report_date)s
				{conditions}
			""",
			self.filters,
			as_dict=1,
		)

		if not pe_rows:
			return [], []

		allocated_rows = frappe.db.sql(
			"""
			SELECT parent, SUM(allocated_amount) AS allocated_total
			FROM `tabPayment Entry Reference`
			WHERE reference_doctype = 'Purchase Invoice'
				AND parent IN %(names)s
			GROUP BY parent
			""",
			{"names": tuple(r.payment_entry for r in pe_rows)},
			as_dict=1,
		)
		allocated_map = {r.parent: flt(r.allocated_total) for r in allocated_rows}

		po_lookup = self.get_po_lookup()
		supplier_meta = self.get_supplier_meta()

		matched, unmatched = [], []
		for d in pe_rows:
			d.allocated_total = allocated_map.get(d.payment_entry, 0.0)
			supplier = self.match_supplier(d.reference_no, po_lookup)
			if not supplier:
				unmatched.append(d)
				continue

			meta = supplier_meta.get(supplier, frappe._dict())
			d.supplier = supplier
			d.supplier_name = meta.get("supplier_name")
			d.supplier_group = meta.get("supplier_group")
			matched.append(d)

		return matched, unmatched

	def get_data(self):
		self.data = []
		report_date = getdate(self.filters.report_date)
		raw_data, unmatched = self.get_raw_data()

		self.unmatched_entries = unmatched

		supplier_filter = None
		if self.filters.get("supplier"):
			supplier_filter = self.filters.get("supplier")
			if isinstance(supplier_filter, str):
				supplier_filter = frappe.parse_json(supplier_filter)
		supplier_group_filter = self.filters.get("supplier_group")

		supplier_total = frappe._dict()

		for d in raw_data:
			if supplier_filter and d.supplier not in supplier_filter:
				continue
			if supplier_group_filter and d.supplier_group != supplier_group_filter:
				continue

			unallocated = flt(d.paid_amount) - flt(d.allocated_total)
			if unallocated <= 0:
				continue

			if d.supplier not in supplier_total:
				supplier_total[d.supplier] = frappe._dict(
					{
						"supplier": d.supplier,
						"supplier_name": d.supplier_name,
						"supplier_group": d.supplier_group,
						"currency": d.currency,
						"outstanding": 0.0,
						"withholding_tax": 0.0,
						"aged_0_30": 0.0,
						"aged_31_60": 0.0,
						"aged_61_90": 0.0,
						"aged_91_120": 0.0,
						"aged_121_above": 0.0,
					}
				)

			row = supplier_total[d.supplier]
			row.outstanding += unallocated
			row.withholding_tax += flt(d.withholding_tax)

			age = max(date_diff(report_date, getdate(d.posting_date)), 0)

			if age <= 30:
				row.aged_0_30 += unallocated
			elif age <= 60:
				row.aged_31_60 += unallocated
			elif age <= 90:
				row.aged_61_90 += unallocated
			elif age <= 120:
				row.aged_91_120 += unallocated
			else:
				row.aged_121_above += unallocated

		self.data = list(supplier_total.values())
