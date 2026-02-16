# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

from datetime import date
import frappe
from frappe import _

def execute(filters=None):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))
	
	asp = float(filters.get("asp") or 0)
	return get_columns(), get_data(filters, asp)

def get_columns():
	return [
		{
			'fieldname': 'posting_date',
			'label': _('Date'),
			'fieldtype': 'Date',
			'width': '150px'
		},
		{
			'fieldname': 'vehicle',
			'label': _('Vehicle'),
			'fieldtype': 'Link',
			'options': 'Warehouse',
			'width': '150px',
		},
		{
			'fieldname': 'driver',
			'label': _('Driver'),
			'fieldtype': 'Data',
			'width': '150px'
		},
		{
			'fieldname': 'source_warehouse',
			'label': _('LC'),
			'fieldtype': 'Link',
			'options': 'Warehouse',
			'width': '150px'
		},
		{
			'fieldname': 'supplier',
			'label': _('Supplier'),
			'fieldtype': 'Link',
			'options': 'Supplier',
			'width': '150px'
		},
		{
			'fieldname': 'total_dispatch',
			'label': _('Total Dispatch'),
			'fieldtype': 'Float',
			'width': '150px'
		},
		{
			'fieldname': 'total_receipt',
			'label': _('Total Receipt'),
			'fieldtype': 'Float',
			'width': '150px'
		},
		{
			'fieldname': 'total_variance',
			'label': _('Total Variance'),
			'fieldtype': 'Float',
			'width': '150px'
		},
		{
			'fieldname': 'variance_percentage',
			'label': _('Variance %'),
			'fieldtype': 'Percent',
			'width': '120px'
		},
		{
			'fieldname': 'threshold',
			'label': _('Threshold'),
			'fieldtype': 'Float',
			'width': '120px'
		},
		{
			'fieldname': 'supplier_loss',
			'label': _('Supplier Loss'),
			'fieldtype': 'Float',
			'width': '150px'
		},
		{
			'fieldname': 'supplier_variance',
			'label': _('Supplier Variance'),
			'fieldtype': 'Float',
			'width': '150px'
		}
	]

def get_data(filters, asp=0):
	company = filters.get("company")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	vehicle = filters.get("vehicle")
	driver = filters.get("driver")
	source_warehouse = filters.get("source_warehouse")
	supplier = filters.get("supplier")
	item_group = filters.get("item_group")

	conditions = " AND se.docstatus = 1 "
	
	#filter by selected item groups
	if item_group:
		item_group_list = "', '".join(item_group) if isinstance(item_group, list) else item_group
		conditions += f" AND sed.item_group IN ('{item_group_list}')"
	
	if company:
		conditions += f" AND se.company = '{company}'"
	
	if vehicle:
		conditions += f" AND se.from_warehouse = '{vehicle}'"
	
	if driver:
		conditions += f" AND se.driver = '{driver}'"
	
	if source_warehouse:
		conditions += f" AND old_sed.s_warehouse = '{source_warehouse}'"
	
	#get dispatch data (outgoing stock entries)
	dispatch_data = frappe.db.sql(f"""
		SELECT 
			se.posting_date,
			se.from_warehouse as vehicle,
			dr.full_name as driver,
			old_sed.s_warehouse as source_warehouse,
			SUM(old_sed.qty) as total_dispatch,
			SUM(old_sed.transferred_qty) as total_receipt,
			SUM(old_sed.qty - old_sed.transferred_qty) as total_variance
		FROM `tabStock Entry Detail` sed
		INNER JOIN `tabStock Entry` se ON se.name = sed.parent
		INNER JOIN `tabStock Entry Detail` old_sed ON sed.ste_detail = old_sed.name
		INNER JOIN `tabStock Entry` old_se ON se.outgoing_stock_entry = old_se.name
		LEFT JOIN `tabDriver` dr ON se.driver = dr.name
		WHERE (se.posting_date BETWEEN '{from_date}' AND '{to_date}') {conditions}
		GROUP BY se.from_warehouse, se.posting_date, old_sed.s_warehouse
		ORDER BY se.posting_date
	""", as_dict=True)
	
	#get unique vehicle warehouses and fetch their suppliers
	vehicle_suppliers = {}
	vehicles = list(set([row['vehicle'] for row in dispatch_data]))
	for veh in vehicles:
		supplier_value = frappe.db.get_value('Warehouse', veh, 'custom_supplier')
		vehicle_suppliers[veh] = supplier_value
	
	#build final data with calculations
	data = []
	for dispatch in dispatch_data:
		posting_date = dispatch.posting_date
		vehicle = dispatch.vehicle
		vehicle_supplier = vehicle_suppliers.get(vehicle)
		
		if supplier and vehicle_supplier != supplier:
			continue
		
		#get receipt for this vehicle and date
		total_receipt = dispatch.total_receipt or 0
		
		#get total dispatch and variance
		total_dispatch = dispatch.total_dispatch or 0
		total_variance = dispatch.total_variance or 0
		
		#calculate variance percentage
		variance_percentage = ((total_variance / total_dispatch) * 100) if total_dispatch > 0 else 0
		
		#calculate threshold (0.45% of total dispatch)
		threshold = (total_dispatch * 0.0045)
		
		#calculate supplier loss: IF(Total Variance - Threshold > 0, Total Variance - Threshold, 0)
		supplier_loss = max(total_variance - threshold, 0)
		
		#calculate supplier variance: Supplier Loss * ASP
		supplier_variance = supplier_loss * asp
		
		data.append({
			'posting_date': posting_date,
			'vehicle': vehicle,
			'driver': dispatch.driver,
			'source_warehouse': dispatch.source_warehouse,
			'supplier': vehicle_supplier,
			'total_dispatch': total_dispatch,
			'total_receipt': total_receipt,
			'total_variance': total_variance,
			'variance_percentage': variance_percentage,
			'threshold': threshold,
			'supplier_loss': supplier_loss,
			'supplier_variance': supplier_variance
		})
	
	return data
