# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, date_diff, getdate
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import AccountsReceivableSummary
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
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		self.get_columns()
		self.get_data(args)
		return self.columns, self.data

	def get_columns(self):
		"""Override to add custom aging buckets"""
		self.columns = []
		
		#Party Columns
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

		#credit days and limit
		self.add_column(label=_("Credit Days"), fieldname="credit_days", fieldtype="Data", width=100)
		self.add_column(label=_("Credit Limit"), fieldname="credit_limit", fieldtype="Currency", width=120)

		self.add_column(label=_("Outstanding Amount"), fieldname="outstanding", fieldtype="Currency", width=120)

		#aged Balances (Not Yet Due) - 5 buckets
		self.add_column(label=_("0-30"), fieldname="not_due_0", fieldtype="Currency", width=100)
		self.add_column(label=_("31-60"), fieldname="not_due_1", fieldtype="Currency", width=100)
		self.add_column(label=_("61-90"), fieldname="not_due_2", fieldtype="Currency", width=100)
		self.add_column(label=_("91-120"), fieldname="not_due_3", fieldtype="Currency", width=100)
		self.add_column(label=_("121-Above"), fieldname="not_due_4", fieldtype="Currency", width=100)

		#overdue Balances - 6 buckets
		self.add_column(label=_("0-7"), fieldname="overdue_0", fieldtype="Currency", width=100)
		self.add_column(label=_("8-30"), fieldname="overdue_1", fieldtype="Currency", width=100)
		self.add_column(label=_("31-60"), fieldname="overdue_2", fieldtype="Currency", width=100)
		self.add_column(label=_("61-90"), fieldname="overdue_3", fieldtype="Currency", width=100)
		self.add_column(label=_("91-120"), fieldname="overdue_4", fieldtype="Currency", width=100)
		self.add_column(label=_("121-Above"), fieldname="overdue_5", fieldtype="Currency", width=100)

		#supplier group and currency
		self.add_column(
			label=_("Supplier Group"),
			fieldname="supplier_group",
			fieldtype="Link",
			options="Supplier Group",
			width=120
		)
		self.add_column(
			label=_("Currency"),
			fieldname="currency",
			fieldtype="Link",
			options="Currency",
			width=80
		)

	def get_data(self, args):
		"""Override to calculate custom aging"""
		self.data = []
		self.receivables = ReceivablePayableReport(self.filters).run(args)[1]
		
		self.party_total = frappe._dict()
		self.calculate_custom_ageing()

		#build final data rows
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
			self.data.append(row)

	def calculate_custom_ageing(self):
		"""Calculate custom aging buckets"""
		report_date = getdate(self.filters.report_date)
		
		for d in self.receivables:
			if d.party not in self.party_total:
				self.init_party_total(d)
				
			outstanding = flt(d.get("outstanding"))
			if outstanding == 0:
				continue
				
			self.party_total[d.party].outstanding += outstanding
			
			#set supplier group and currency
			if d.get("supplier_group"):
				self.party_total[d.party].supplier_group = d.get("supplier_group")
			if d.get("currency"):
				self.party_total[d.party].currency = d.get("currency")
			
			#get due date or fallback to posting date
			due_date = d.get("due_date")
			if not due_date:
				due_date = d.get("posting_date")
			due_date = getdate(due_date)
			
			if due_date <= report_date:
				#overdue calculation
				age = date_diff(report_date, due_date)
				if age < 0:
					age = 0
				
				#overdue
				if age <= 7:
					index = 0
				elif age <= 30:
					index = 1
				elif age <= 60:
					index = 2
				elif age <= 90:
					index = 3
				elif age <= 120:
					index = 4
				else:
					index = 5
				
				self.party_total[d.party][f"overdue_{index}"] += outstanding
			else:
				#days until due
				days_until = date_diff(due_date, report_date)
				
				#overdue
				if days_until <= 30:
					index = 0
				elif days_until <= 60:
					index = 1
				elif days_until <= 90:
					index = 2
				elif days_until <= 120:
					index = 3
				else:
					index = 4
				
				self.party_total[d.party][f"not_due_{index}"] += outstanding

	def init_party_total(self, row):
		"""Initialize party totals with custom buckets"""
		default_dict = {
			"outstanding": 0.0,
			"credit_days": "",
			"credit_limit": 0.0,
			"party_type": row.party_type,
			"supplier_group": "",
			"currency": "",
		}
		
		#aged
		for i in range(5):
			default_dict[f"not_due_{i}"] = 0.0
		
		#overdue
		for i in range(6):
			default_dict[f"overdue_{i}"] = 0.0
			
		self.party_total[row.party] = frappe._dict(default_dict)
