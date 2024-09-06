# Copyright (c) 2024, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if from_date > to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))

    def get_columns():
        return [
            {
                "fieldname": "item_code",
                "label": _("Item Code"),
                "fieldtype": "Link",
                "options": "Item",
                "width": "150px"
            },
            {
                "fieldname": "item_name",
                "label": _("Item Name"),
                "fieldtype": "Data",
                "width": "150px"
            },
            {
                "fieldname": "qty",
                "label": _("Qty"),
                "fieldtype": "Float",
                "width": "100px"
            },
            {
                "fieldname": "avg_selling_amount",
                "label": _("Avg Selling Rate"),
                "fieldtype": "Currency",
                "width": "100px"
            },
            {
                "fieldname": "selling_amount",
                "label": _("Selling Amount"),
                "fieldtype": "Currency",
                "options": "Currency",
                "width": "100px"
            },
            {
                "fieldname": "gross_profit",
                "label": _("Gross Profit"),
                "fieldtype": "Currency",
                "width": "100px"
            },
            {
                "fieldname": "gross_profit_percent",
                "label": _("Gross Profit Percent"),
                "fieldtype": "Percent",
                "width": "100px"
            },
        ]

    def get_data():
        conditions = " AND si.docstatus = 1 "
        if company:
            conditions += f" AND si.company = '{company}'"

        conditions += " AND sii.item_group = 'Gutted Fish-Tilapia'"

        sales_invoice_items = frappe.db.sql(f"""
            SELECT sii.item_code 'item_code',
                sii.item_name 'item_name', 
                SUM(sii.stock_qty) 'qty',
                SUM(sii.base_net_amount) 'selling_amount',
                SUM(sii.base_net_amount) - SUM(sii.base_net_rate * sii.stock_qty) AS 'gross_profit',
                ((SUM(sii.base_net_amount) - SUM(sii.base_net_rate * sii.stock_qty)) / SUM(sii.base_net_amount)) * 100 AS 'gross_profit_percent'
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON sii.parent = si.name
            WHERE (si.posting_date BETWEEN '{from_date}' AND '{to_date}') {conditions}
            GROUP BY sii.item_code
        """, as_dict=True)

        for item in sales_invoice_items:
            item['avg_selling_amount'] = item['selling_amount'] / item['qty'] if item.get('selling_amount') and item.get('qty') else 0
            
        # frappe.log_error(message=f"Qty Value:{item.get('qty')}, Type:{type(item.get('qty'))}", title="Qty Debug")

        return sales_invoice_items

    columns, data = get_columns(), get_data()

    chart = {
        "data": {
            "labels": [row["item_code"] for row in data],
            "datasets": [
                {
                    "name": _("Qty"),
                    "values": [row["qty"] for row in data]
                },
                {
                    "name": _("Selling Amount"),
                    "values": [row["selling_amount"] for row in data]
                }
            ]
        },
        "type": "bar",
        "height": 300,
        "colors":[ "#10812E","#61CE70"]
    }

    return columns, data, None, chart
