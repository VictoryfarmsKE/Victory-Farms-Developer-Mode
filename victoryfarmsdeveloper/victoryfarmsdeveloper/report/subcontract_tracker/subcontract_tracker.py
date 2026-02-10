# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.utils import flt


def execute(filters=None):
	"""Return columns and data for SubContract Tracker report
 
	"""
	filters = filters or {}

	columns = [
        "Contracts:Data:140",
		"Contractor Name:Data:160",
		"Contractor Contact:Data:140",
		# "Project:Data:140",
		"Capex ID:Data:80",
		"Project Name:Data:220",
		"Total Amount:Currency:120",
  		"PO Number:Link/Purchase Order:130",
		# "Supplier:Link/Supplier:150",
		"Receipted:Currency:120",
		"Amount Paid:Currency:120",
		"Balance:Currency:120",
		"Percentage Paid:Percent:100",
		# "Work Status:Data:120",
		# "Date Signed:Date:100",
	]

	data = []

	conditions = ["po.docstatus = 1"]
	params = []

	# Only consider Purchase Orders for contractor payments
	conditions.append("po.custom_supplier_group = %s")
	params.append("Construction contractors")

	if filters.get("purchase_order"):
		conditions.append("po.name = %s")
		params.append(filters.get("purchase_order"))

	if filters.get("project"):
		conditions.append("po.project = %s")
		params.append(filters.get("project"))

	where = " AND ".join(conditions)

	pos = frappe.db.sql(
		f"""
		SELECT
			po.name as name,
			po.supplier as supplier,
			po.project as project,
			po.contact_display as contact_display,
			po.contact_mobile as contact_mobile,
			IFNULL(po.grand_total, 0) as grand_total
		FROM `tabPurchase Order` po
		WHERE {where}
		ORDER BY po.modified DESC
		""",
		tuple(params),
		as_dict=True,
	)

	for po in pos:
		po_name = po.get("name")

		# Sum of linked Purchase Receipts (link is on Purchase Receipt Item.purchase_order)
		receipted = flt(
			frappe.db.sql(
				"""SELECT IFNULL(SUM(pr.grand_total), 0) 
				FROM `tabPurchase Receipt` pr 
				WHERE pr.docstatus = 1 AND pr.name IN (
					SELECT DISTINCT pri.parent 
					FROM `tabPurchase Receipt Item` pri 
					WHERE pri.purchase_order = %s
				)""",
				(po_name,),
			)[0][0]
		)

		# Gather purchase invoices linked to this PO via Purchase Invoice Item.purchase_order
		invoices = frappe.db.sql(
			"""
			SELECT
				pi.name AS name,
				IFNULL(pi.grand_total, 0) AS grand_total,
				IFNULL(pi.outstanding_amount, 0) AS outstanding_amount
			FROM `tabPurchase Invoice` pi
			JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
			WHERE pii.purchase_order = %s AND pi.docstatus = 1
			GROUP BY pi.name, pi.grand_total, pi.outstanding_amount
			""",
			po_name,
			as_dict=True,
		)
		amount_paid = flt(sum([flt(inv.get("grand_total") or 0) - flt(inv.get("outstanding_amount") or 0) for inv in invoices]))

		total_amount = flt(po.get("grand_total") or 0)
		balance = flt(total_amount - amount_paid)

		percentage_paid = 0.0
		if total_amount:
			# percentage of the PO that has been paid
			percentage_paid = flt((amount_paid / total_amount) * 100)

		# Get project display value (Project.project_name if available, else Project.name)
		project_value = po.get("project") or ""
		project_display = project_value
		if project_value:
			proj_doc = frappe.db.get_value("Project", project_value, ["project_name", "name"], as_dict=True)
			if proj_doc:
				project_display = proj_doc.get("project_name") or proj_doc.get("name") or project_value
		capex_id = ""
		project_name = ""
		if project_display:
			m = re.search(r"CAPEX\s*ID\s*(\d+)\s*:\s*(.+)", project_display, re.I)
			if m:
				capex_id = m.group(1)
				project_name = m.group(2).strip()
			else:
				m2 = re.search(r"(\d+)\s*[:\-]\s*(.+)", project_display)
				if m2:
					capex_id = m2.group(1)
					project_name = m2.group(2).strip()
				else:
					project_name = project_display

		# Contracts: first row 'description' from Purchase Order Item child table
		contracts = ""
		po_item = frappe.db.sql(
			"SELECT description FROM `tabPurchase Order Item` WHERE parent = %s AND IFNULL(description, '') != '' ORDER BY idx ASC LIMIT 1",
			(po_name,),
			as_dict=True,
		)
		if po_item and po_item[0].get("description"):
			contracts = po_item[0].get("description")

		# Contractor details from Purchase Order fields
		contractor_name = po.get("contact_display") or ""
		contractor_contact = po.get("contact_mobile") or ""
		work_status = filters.get("work_status") or ""
		date_signed = None

		row = [
			contracts,
			contractor_name,
			contractor_contact,
			# po.get("supplier"),
			# project_display,
			capex_id,
			project_name,
			total_amount,	
			po_name,
			receipted,
			to_pay,
			amount_paid,
			balance,
			percentage_paid,
			# work_status,
			# date_signed,
		]

		data.append(row)

	return columns, data
