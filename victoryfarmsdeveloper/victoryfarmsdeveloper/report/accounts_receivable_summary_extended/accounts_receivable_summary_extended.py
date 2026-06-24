# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
from frappe.utils import cint, flt, date_diff, getdate

from erpnext.accounts.party import get_partywise_advanced_payment_amount
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
from erpnext.accounts.utils import get_currency_precision, get_party_types_from_account_type


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivableSummaryExtended(filters).run(args)


class AccountsReceivableSummaryExtended(ReceivablePayableReport):
	def run(self, args):
		self.account_type = args.get("account_type")
		self.party_type = get_party_types_from_account_type(self.account_type)
		self.party_naming_by = frappe.db.get_single_value(args.get("naming_by")[0], args.get("naming_by")[1])
		self.get_columns()
		self.get_data(args)
		return self.columns, self.data

	def get_data(self, args):
		self.data = []
		self.receivables = ReceivablePayableReport(self.filters).run(args)[1]
		self.currency_precision = get_currency_precision() or 2

		self.get_party_total(args)

		party = None
		for party_type in self.party_type:
			if self.filters.get(scrub(party_type)):
				party = self.filters.get(scrub(party_type))

		party_advance_amount = (
			get_partywise_advanced_payment_amount(
				self.party_type,
				self.filters.report_date,
				self.filters.show_future_payments,
				self.filters.company,
				party=party,
			)
			or {}
		)

		if self.filters.show_gl_balance:
			gl_balance_map = get_gl_balance(self.filters.report_date, self.filters.company, self.account_type)

		self.calculate_custom_ageing()
		self.customer_credit_map = self.get_customer_credit_terms()

		for party, party_dict in self.party_total.items():
			if flt(party_dict.outstanding, self.currency_precision) == 0:
				continue

			row = frappe._dict()

			row.party = party
			if self.party_naming_by == "Naming Series":
				if self.account_type == "Payable":
					doctype = "Supplier"
					fieldname = "supplier_name"
				else:
					doctype = "Customer"
					fieldname = "customer_name"
				row.party_name = frappe.get_cached_value(doctype, party, fieldname)

			row.update(party_dict)

			# Add credit days and credit limit
			credit = self.customer_credit_map.get(party, frappe._dict())
			row.credit_days = cint(credit.get("credit_days"))
			row.credit_limit = flt(credit.get("credit_limit")) if credit.get("credit_limit") else 0.0

			# Advance against party
			row.advance = party_advance_amount.get(party, 0)

			# In AR/AP, advance shown in paid columns,
			# but in summary report advance shown in separate column
			row.paid -= row.advance

			if self.filters.show_gl_balance:
				row.gl_balance = gl_balance_map.get(party)
				row.diff = flt(row.outstanding) - flt(row.gl_balance)

			if self.filters.show_future_payments:
				row.remaining_balance = flt(row.outstanding) - flt(row.future_amount)

			self.data.append(row)

	def get_party_total(self, args):
		self.party_total = frappe._dict()

		for d in self.receivables:
			self.init_party_total(d)

			# Add all amount columns
			for k in list(self.party_total[d.party]):
				if isinstance(self.party_total[d.party][k], float):
					self.party_total[d.party][k] += d.get(k) or 0.0

			# set territory, customer_group, sales person etc
			self.set_party_details(d)

	def init_party_total(self, row):
		default_dict = {
			"invoiced": 0.0,
			"paid": 0.0,
			"credit_note": 0.0,
			"outstanding": 0.0,
			"total_due": 0.0,
			"future_amount": 0.0,
			"credit_days": 0,
			"credit_limit": 0.0,
			"sales_person": [],
			"party_type": row.party_type,
			# Section A - Aged Balance
			"aged_0_30": 0.0,
			"aged_31_60": 0.0,
			"aged_61_90": 0.0,
			"aged_91_120": 0.0,
			"aged_121_above": 0.0,
			# Section B - Overdue Balance
			"overdue_0_7": 0.0,
			"overdue_8_15": 0.0,
			"overdue_16_30": 0.0,
			"overdue_31_45": 0.0,
			"overdue_45_above": 0.0,
		}
		for i in self.range_numbers:
			range_key = f"range{i}"
			default_dict[range_key] = 0.0

		self.party_total.setdefault(
			row.party,
			frappe._dict(default_dict),
		)

	def calculate_custom_ageing(self):
		"""
		SECTION A - Aged Balance
		  age = report_date - posting_date (invoice date)

		SECTION B - Overdue Balance
		  days_overdue = report_date - due_date  (only when overdue)
		"""
		report_date = getdate(self.filters.report_date)

		for d in self.receivables:
			outstanding = flt(d.get("outstanding"))
			if outstanding == 0:
				continue

			if d.party not in self.party_total:
				continue  # already initialised by get_party_total

			# --- Section A: Aged Balance (age from invoice posting_date) ---
			invoice_date = getdate(d.get("posting_date") or report_date)
			age = max(date_diff(report_date, invoice_date), 0)

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

			# --- Section B: Overdue Balance (days past due_date) ---
			due_date = getdate(d.get("due_date") or report_date)

			if due_date < report_date:
				days_overdue = max(date_diff(report_date, due_date), 0)

				if days_overdue <= 7:
					self.party_total[d.party].overdue_0_7 += outstanding
				elif days_overdue <= 15:
					self.party_total[d.party].overdue_8_15 += outstanding
				elif days_overdue <= 30:
					self.party_total[d.party].overdue_16_30 += outstanding
				elif days_overdue <= 45:
					self.party_total[d.party].overdue_31_45 += outstanding
				else:
					self.party_total[d.party].overdue_45_above += outstanding

	def set_party_details(self, row):
		self.party_total[row.party].currency = row.currency

		for key in ("territory", "customer_group", "supplier_group"):
			if row.get(key):
				self.party_total[row.party][key] = row.get(key, "")
		if row.sales_person:
			self.party_total[row.party].sales_person.append(row.get("sales_person", ""))

		if self.filters.sales_partner:
			self.party_total[row.party]["default_sales_partner"] = row.get("default_sales_partner", "")

	def get_columns(self):
		self.columns = []
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
			)

		credit_debit_label = "Credit Note" if self.account_type == "Receivable" else "Debit Note"

		# Credit terms
		self.add_column(label=_("Credit Days"), fieldname="credit_days", fieldtype="Int", width=100)
		self.add_column(label=_("Credit Limit"), fieldname="credit_limit", fieldtype="Currency", width=130)

		self.add_column(_("Advance Amount"), fieldname="advance")
		self.add_column(_("Invoiced Amount"), fieldname="invoiced")
		self.add_column(_("Paid Amount"), fieldname="paid")
		self.add_column(_(credit_debit_label), fieldname="credit_note")
		self.add_column(_("Outstanding Amount"), fieldname="outstanding")

		if self.filters.show_gl_balance:
			self.add_column(_("GL Balance"), fieldname="gl_balance")
			self.add_column(_("Difference"), fieldname="diff")

		self.setup_ageing_columns()
		self.add_column(label=_("Total Amount Due"), fieldname="total_due")

		# Section A - Aged Balance (age from invoice date)
		# self.add_column(label=_("0-30"), fieldname="aged_0_30", fieldtype="Currency", width=120)
		# self.add_column(label=_("31-60"), fieldname="aged_31_60", fieldtype="Currency", width=120)
		# self.add_column(label=_("61-90"), fieldname="aged_61_90", fieldtype="Currency", width=120)
		# self.add_column(label=_("91-120"), fieldname="aged_91_120", fieldtype="Currency", width=120)
		# self.add_column(label=_("121 and above"), fieldname="aged_121_above", fieldtype="Currency", width=130)

		# Section B - Overdue Balance (days past due date)
		self.add_column(label=_("0-7"), fieldname="overdue_0_7", fieldtype="Currency", width=120)
		self.add_column(label=_("8-15"), fieldname="overdue_8_15", fieldtype="Currency", width=120)
		self.add_column(label=_("16-30"), fieldname="overdue_16_30", fieldtype="Currency", width=120)
		self.add_column(label=_("31-45"), fieldname="overdue_31_45", fieldtype="Currency", width=120)
		self.add_column(label=_("45+"), fieldname="overdue_45_above", fieldtype="Currency", width=130)

		if self.filters.show_future_payments:
			self.add_column(label=_("Future Payment Amount"), fieldname="future_amount")
			self.add_column(label=_("Remaining Balance"), fieldname="remaining_balance")

		if self.account_type == "Receivable":
			self.add_column(
				label=_("Territory"), fieldname="territory", fieldtype="Link", options="Territory"
			)
			self.add_column(
				label=_("Customer Group"),
				fieldname="customer_group",
				fieldtype="Link",
				options="Customer Group",
			)
			if self.filters.show_sales_person:
				self.add_column(label=_("Sales Person"), fieldname="sales_person", fieldtype="Data")

			if self.filters.sales_partner:
				self.add_column(label=_("Sales Partner"), fieldname="default_sales_partner", fieldtype="Data")

		else:
			self.add_column(
				label=_("Supplier Group"),
				fieldname="supplier_group",
				fieldtype="Link",
				options="Supplier Group",
			)

		self.add_column(
			label=_("Currency"), fieldname="currency", fieldtype="Link", options="Currency", width=80
		)

	def get_customer_credit_terms(self):
		"""
		Returns a dict keyed by customer/supplier name:
		  {party: {credit_days: int, credit_limit: float}}

		Credit days are read from the first row of Payment Terms Template Detail
		(child table of Payment Terms Template) linked on the Customer/Supplier master
		via the payment_terms field.

		Credit limit is read directly from the Customer/Supplier master credit_limit field.
		"""
		if self.account_type == "Receivable":
			doctype = "Customer"
		else:
			doctype = "Supplier"

		table = f"tab{doctype}"

		# Check once whether credit_limit column exists in the DB.
		# frappe.db.has_column expects the DocType name (it prepends "tab" itself),
		# so pass `doctype` ("Customer"/"Supplier"), not the raw table name.
		has_credit_limit = frappe.db.has_column(doctype, "credit_limit")

		if has_credit_limit:
			parties = frappe.db.sql(
				f"SELECT `name`, `payment_terms`, `credit_limit` FROM `{table}`",
				as_dict=True,
			)
		else:
			parties = frappe.db.sql(
				f"SELECT `name`, `payment_terms` FROM `{table}`",
				as_dict=True,
			)

		templates = {p.payment_terms for p in parties if p.payment_terms}

		template_credit_days = {}
		if templates:
			template_details = frappe.db.get_all(
				"Payment Terms Template Detail",
				fields=["parent", "credit_days"],
				filters={"parent": ["in", list(templates)]},
				order_by="parent, idx",
			)

			for detail in template_details:
				if detail.parent not in template_credit_days:
					template_credit_days[detail.parent] = detail.credit_days

		credit_map = {}
		for party in parties:
			credit_days = template_credit_days.get(party.payment_terms, 0) if party.payment_terms else 0
			credit_limit = flt(party.get("credit_limit")) if has_credit_limit else 0.0

			credit_map[party.name] = frappe._dict(
				{
					"credit_days": credit_days,
					"credit_limit": credit_limit,
				}
			)

		return credit_map


def get_gl_balance(report_date, company, account_type):
	if account_type == "Payable":
		balance_calc_fields = ["party", {"SUM": [{"SUB": ["credit", "debit"]}], "as": "balance"}]
	else:
		balance_calc_fields = ["party", {"SUM": [{"SUB": ["debit", "credit"]}], "as": "balance"}]
	return frappe._dict(
		frappe.db.get_all(
			"GL Entry",
			fields=balance_calc_fields,
			filters={"posting_date": ("<=", report_date), "is_cancelled": 0, "company": company},
			group_by="party",
			as_list=1,
		)
	)
