# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, date_diff, getdate


def execute(filters=None):
	return AdvancesAgeing(filters).run()


class AdvancesAgeing:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.report_date = self.filters.report_date or frappe.utils.today()

	def run(self):
		self.get_columns()
		self.get_data()
		return self.columns, self.data

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

	def get_conditions(self):
		conditions = ""
		if self.filters.get("company"):
			conditions += " AND pe.company = %(company)s"
		if self.filters.get("supplier"):
			suppliers = self.filters.get("supplier")
			if isinstance(suppliers, str):
				suppliers = frappe.parse_json(suppliers)
			if suppliers:
				conditions += " AND po.supplier IN %(supplier)s"
				self.filters.supplier = tuple(suppliers)
		if self.filters.get("supplier_group"):
			conditions += " AND s.supplier_group = %(supplier_group)s"
		return conditions

	def get_raw_data(self):
		conditions = self.get_conditions()

		return frappe.db.sql(
			f"""
			SELECT
				pe.name AS payment_entry,
				po.supplier AS supplier,
				s.supplier_name AS supplier_name,
				s.supplier_group AS supplier_group,
				pe.posting_date AS posting_date,
				pe.paid_amount AS paid_amount,
				pe.paid_from_account_currency AS currency,
				pe.custom_withholding_taxes AS withholding_tax,
				COALESCE(per.allocated_total, 0) AS allocated_total
			FROM `tabPayment Entry` pe
			INNER JOIN `tabPurchase Order` po ON pe.reference_no = po.name
			INNER JOIN `tabSupplier` s ON s.name = po.supplier
			LEFT JOIN (
				SELECT parent, SUM(allocated_amount) AS allocated_total
				FROM `tabPayment Entry Reference`
				WHERE reference_doctype = 'Purchase Invoice'
				GROUP BY parent
			) per ON per.parent = pe.name
			WHERE
				pe.docstatus = 1
				AND pe.payment_type = 'Internal Transfer'
				AND pe.posting_date <= %(report_date)s
				{conditions}
			ORDER BY po.supplier, pe.posting_date
			""",
			self.filters,
			as_dict=1,
		)

	def get_data(self):
		self.data = []
		report_date = getdate(self.filters.report_date)
		raw_data = self.get_raw_data()

		supplier_total = frappe._dict()

		for d in raw_data:
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
