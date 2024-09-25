import frappe
from frappe import _

def execute(filters=None):
    columns, data = get_stock_balance_data(filters)
    return columns, data

def get_stock_balance_data(filters):
    # Define columns
    columns = [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
        {"label": _("Opening Qty"), "fieldname": "opening_qty", "fieldtype": "Float", "width": 100},
        {"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Balance Qty"), "fieldname": "bal_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Valuation Rate"), "fieldname": "val_rate", "fieldtype": "Currency", "options": "Company:company:default_currency", "width": 100},
        {"label": _("Balance Value"), "fieldname": "bal_val", "fieldtype": "Currency", "options": "Company:company:default_currency", "width": 100},
    ]

    # Add additional UOM columns if needed
    if filters.get("include_uom"):
        additional_uom_columns = get_additional_uom_columns(filters.get("include_uom"))
        columns.extend(additional_uom_columns)

    # Fetch data from the Stock Ledger Entry
    sle = frappe.qb.DocType("Stock Ledger Entry")
    item_table = frappe.qb.DocType("Item")

    query = (
        frappe.qb.from_(sle)
        .inner_join(item_table)
		.on(sle.item_code == item_table.name)
        .select(
            sle.item_code,
            sle.item_code.as_("name"),
            sle.stock_uom,
            sle.actual_qty,
            sle.valuation_rate,
            sle.stock_value,
            sle.posting_date,
            item_table.item_group,
			item_table.stock_uom,
			item_table.item_name
        )
        .where(
            (sle.docstatus < 2) & (sle.is_cancelled == 0) &
            (sle.posting_date >= filters.get("from_date")) &
            (sle.posting_date <= filters.get("to_date"))
        )
        .orderby(sle.item_code)
    )
    
    # Apply filters
    if filters.get("company"):
        query = query.where(sle.company == filters.get("company"))
    if filters.get("item_code"):
        query = query.where(sle.item_code == filters.get("item_code"))

    # Execute query
    data = frappe.db.sql(query, as_dict=True)

    # Group data by item_code
    grouped_data = {}
    for entry in data:
        item_code = entry['item_code']
        if item_code not in grouped_data:
            grouped_data[item_code] = {
                "item_code": entry["item_code"],
                "item_name": entry["item_name"],
                "stock_uom": entry["stock_uom"],
                "opening_qty": 0.0,
                "in_qty": 0.0,
                "out_qty": 0.0,
                "bal_qty": 0.0,
                "val_rate": 0.0,
                "bal_val": 0.0
            }
        
        # Calculate quantities and values
        grouped_data[item_code]["in_qty"] += max(entry["actual_qty"], 0)
        grouped_data[item_code]["out_qty"] += abs(min(entry["actual_qty"], 0))
        grouped_data[item_code]["bal_qty"] += entry["actual_qty"]
        grouped_data[item_code]["bal_val"] += entry["stock_value"]
        grouped_data[item_code]["val_rate"] = entry["valuation_rate"]

    # Convert to list for output
    output_data = list(grouped_data.values())

    return columns, output_data

def get_additional_uom_columns(uom):
    return [
        {"label": f"Qty ({uom})", "fieldname": f"qty_{uom}", "fieldtype": "Float", "width": 100},
        {"label": f"Value ({uom})", "fieldname": f"value_{uom}", "fieldtype": "Currency", "width": 100},
    ]
