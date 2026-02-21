# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, date_diff, getdate

from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
AccountsReceivableSummary,
)
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
from erpnext.accounts.utils import get_party_types_from_account_type


def execute(filters=None):
	args = {
	"account_type": "Payable",
	"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return AccountsPayableSummaryExtended(filters).run(args)


class AccountsPayableSummaryExtended(AccountsReceivableSummary):
	def run(self, args):
		self.account_type = args.get("account_type")
		self.party_type = get_party_types_from_account_type(self.account_type)
		self.party_naming_by = frappe.db.get_value(
			args.get("naming_by")[0], None, args.get("naming_by")[1]
		)
		self.get_columns()
		self.get_data(args)
		return self.columns, self.data

	def get_columns(self):
		self.columns = []

		# Party identifiers
		self.add_column(
			label=_("Party Type"),
			fieldname="party_type",
			fieldtype="Data",
			width=100,
		)
		self.add_column(
			label=_("Party"),
			fieldname="party",
			fieldtype="Dynamic Link",
			options="party_type",
			width=180,
		)
		if self.party_naming_by == "Naming Series":
			self.add_column(
				label=_("Supplier Name") if self.account_type == "Payable" else _("Customer Name"),
				fieldname="party_name",
				fieldtype="Data",
				width=180,
			)

		# Credit terms
		self.add_column(label=_("Credit Days"), fieldname="credit_days", fieldtype="Int", width=100)
		self.add_column(label=_("Credit Limit"), fieldname="credit_limit", fieldtype="Currency", width=130)

		# Total outstanding
		self.add_column(
			label=_("Outstanding Amount"), fieldname="outstanding", fieldtype="Currency", width=140
		)

		# -- SECTION A: Aged Balance (days since posting date) --
		self.add_column(
			label=_("Aged Balance: 0-30"), fieldname="aged_0_30", fieldtype="Currency", width=120
		)
		self.add_column(
			label=_("Aged Balance: 31-60"), fieldname="aged_31_60", fieldtype="Currency", width=120
		)
		self.add_column(
			label=_("Aged Balance: 61-90"), fieldname="aged_61_90", fieldtype="Currency", width=120
		)
		self.add_column(
			label=_("Aged Balance: 91-120"), fieldname="aged_91_120", fieldtype="Currency", width=120
		)
		self.add_column(
			label=_("Aged Balance: 121-Above"), fieldname="aged_121_above", fieldtype="Currency", width=130
		)

		# -- SECTION B: Overdue Balance (days past due date) --
		self.add_column(
			label=_("Overdue Balance: 0-7 (Suboptimal Terms)"),
			fieldname="overdue_0_7",
			fieldtype="Currency",
			width=180,
		)
		self.add_column(
			label=_("Overdue Balance: 8-30"), fieldname="overdue_8_30", fieldtype="Currency", width=130
		)
		self.add_column(
			label=_("Overdue Balance: 31-60"), fieldname="overdue_31_60", fieldtype="Currency", width=130
		)
		self.add_column(
			label=_("Overdue Balance: 61-90"), fieldname="overdue_61_90", fieldtype="Currency", width=130
		)
		self.add_column(
			label=_("Overdue Balance: 91-120"), fieldname="overdue_91_120", fieldtype="Currency", width=140
		)
		self.add_column(
			label=_("Overdue Balance: 121-Above"),
			fieldname="overdue_121_above",
			fieldtype="Currency",
			width=150,
		)

		# Supplier group and currency
		self.add_column(
			label=_("Supplier Group"),
			fieldname="supplier_group",
			fieldtype="Link",
			options="Supplier Group",
			width=130,
		)
		self.add_column(
			label=_("Currency"),
			fieldname="currency",
			fieldtype="Link",
			options="Currency",
			width=80,
		)

	def get_data(self, args):
		self.data = []
		self.receivables = ReceivablePayableReport(self.filters).run(args)[1]

		self.party_total = frappe._dict()
		self.calculate_custom_ageing()

		supplier_credit_map = self.get_supplier_credit_terms()

		for party, party_dict in self.party_total.items():
			if flt(party_dict.outstanding) == 0:
				continue

			row = frappe._dict()
			row.party = party

			if self.party_naming_by == "Naming Series":
				if self.account_type == "Payable":
					row.party_name = frappe.get_cached_value("Supplier", party, "supplier_name")
				else:
					row.party_name = frappe.get_cached_value("Customer", party, "customer_name")

			row.update(party_dict)

			# Set credit terms after update() so they override the zero-defaults in party_dict
			credit = supplier_credit_map.get(party, frappe._dict())
			row.credit_days = cint(credit.get("credit_days"))
			row.credit_limit = flt(credit.get("credit_limit")) if credit.get("credit_limit") else 0.0

			self.data.append(row)


	def calculate_custom_ageing(self):
		"""
		SECTION A - Aged Balance
		  Every invoice is bucketed by age since posting date
		  (report_date - posting_date). Covers ALL outstanding invoices and
		  provides forward visibility for cash planning before invoices fall due.

		SECTION B - Overdue Balance
		  Only invoices where due_date <= report_date are bucketed here,
		  by days past due (report_date - due_date).
		  The 0-7 bucket flags suppliers with potentially suboptimal credit terms.
		"""
		report_date = getdate(self.filters.report_date)

		for d in self.receivables:
			if d.party not in self.party_total:
				self.init_party_total(d)

			outstanding = flt(d.get("outstanding"))
			if outstanding == 0:
				continue

			self.party_total[d.party].outstanding += outstanding

			if d.get("supplier_group"):
				self.party_total[d.party].supplier_group = d.get("supplier_group")
			if d.get("currency"):
				self.party_total[d.party].currency = d.get("currency")

			# Section A: age by posting date (all invoices)
			posting_date = getdate(d.get("posting_date") or report_date)
			age = max(date_diff(report_date, posting_date), 0)

			if age <= 30:
				self.party_total[d.party].aged_0_30 += outstanding
			elif age <= 60:
				self.party_total[d.party].aged_31_60 += outstanding
			elif age <= 90:
				self.party_total[d.party].aged_61_90 += outstanding
			elif age <= 120:
				self.party_total[d.party].aged_91_120 += outstanding
			else:
				self.party_total[d.party].aged_121_above += outstanding

			# Section B: overdue only (due_date <= report_date)
			due_date = getdate(d.get("due_date") or d.get("posting_date") or report_date)

			if due_date <= report_date:
				days_overdue = max(date_diff(report_date, due_date), 0)

				if days_overdue <= 7:
					self.party_total[d.party].overdue_0_7 += outstanding
				elif days_overdue <= 30:
					self.party_total[d.party].overdue_8_30 += outstanding
				elif days_overdue <= 60:
					self.party_total[d.party].overdue_31_60 += outstanding
				elif days_overdue <= 90:
					self.party_total[d.party].overdue_61_90 += outstanding
				elif days_overdue <= 120:
					self.party_total[d.party].overdue_91_120 += outstanding
				else:
					self.party_total[d.party].overdue_121_above += outstanding

	def init_party_total(self, row):
		self.party_total[row.party] = frappe._dict(
			{
				"party_type": row.party_type,
				"outstanding": 0.0,
				"credit_days": 0,
				"credit_limit": 0.0,
				"supplier_group": "",
				"currency": "",
				# Section A - Aged Balance
				"aged_0_30": 0.0,
				"aged_31_60": 0.0,
				"aged_61_90": 0.0,
				"aged_91_120": 0.0,
				"aged_121_above": 0.0,
				# Section B - Overdue Balance
				"overdue_0_7": 0.0,
				"overdue_8_30": 0.0,
				"overdue_31_60": 0.0,
				"overdue_61_90": 0.0,
				"overdue_91_120": 0.0,
				"overdue_121_above": 0.0,
			}
		)

	def get_supplier_credit_terms(self):
		"""
		Returns a dict keyed by supplier name:
		  {supplier: {credit_days: int, credit_limit: float}}

		Credit days are read from the first row of Payment Terms Template Detail
		(child table of Payment Terms Template) linked on the Supplier master
		via the payment_terms field.

		Credit limit is read directly from the Supplier master credit_limit field.
		"""
		suppliers = frappe.db.get_all(
			"Supplier",
			fields=["name", "payment_terms"],
		)

		# Collect unique payment term template names for a single bulk query
		templates = {s.payment_terms for s in suppliers if s.payment_terms}

		# Fetch the first (lowest idx) detail row per template in one query
		template_credit_days = {}
		if templates:
			rows = frappe.db.get_all(
				"Payment Terms Template Detail",
				filters={"parent": ("in", list(templates))},
				fields=["parent", "credit_days"],
				order_by="parent asc, idx asc",
			)
			for row in rows:
				# Keep only the first row per template (primary terms)
				if row.parent not in template_credit_days:
					template_credit_days[row.parent] = cint(row.credit_days)

		result = frappe._dict()
		for supplier in suppliers:
			credit_days = (
				template_credit_days.get(supplier.payment_terms, 0) if supplier.payment_terms else 0
			)
			result[supplier.name] = frappe._dict(
				{
					"credit_days": credit_days,
					"credit_limit": flt(supplier.credit_limit) if supplier.credit_limit else 0.0,
				}
			)

		return result
