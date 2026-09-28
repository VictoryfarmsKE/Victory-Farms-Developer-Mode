# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

LINE_TYPES = ("Harvesting of Fish", "Fish Processing SUVAC", "Fish Processing")


def execute(filters=None):
    filters = frappe._dict(filters or {})
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": _("Stock Entry Type"), "fieldname": "stock_entry_type", "fieldtype": "Data", "width": 170},
        {"label": _("Processing Line"), "fieldname": "processing_line", "fieldtype": "Int", "width": 110},
        {"label": _("Item"), "fieldname": "item_code", "fieldtype": "Data", "width": 220},
        {"label": _("Input Qty"), "fieldname": "input_qty", "fieldtype": "Float", "width": 110},
        {"label": _("Output Qty"), "fieldname": "output_qty", "fieldtype": "Float", "width": 110},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 70},
        {"label": _("Yield %"), "fieldname": "yield_pct", "fieldtype": "Percent", "width": 90},
        {"label": _("Entries"), "fieldname": "entries", "fieldtype": "Int", "width": 80},
    ]


def get_rows(filters):
    se = frappe.qb.DocType("Stock Entry")
    sed = frappe.qb.DocType("Stock Entry Detail")

    types = [filters.stock_entry_type] if filters.stock_entry_type else list(LINE_TYPES)

    query = (
        frappe.qb.from_(sed)
        .join(se)
        .on(se.name == sed.parent)
        .select(
            se.name.as_("stock_entry"),
            se.posting_date,
            se.stock_entry_type,
            sed.custom_line.as_("processing_line"),
            sed.item_code,
            sed.stock_uom.as_("uom"),
            sed.s_warehouse,
            sed.t_warehouse,
            sed.transfer_qty.as_("qty"),
        )
        .where(se.docstatus == 1)
        .where(se.posting_date.between(filters.from_date, filters.to_date))
        .where(se.stock_entry_type.isin(types))
        .orderby(se.posting_date)
        .orderby(se.stock_entry_type)
        .orderby(sed.custom_line)
    )

    if filters.processing_line:
        query = query.where(sed.custom_line == filters.processing_line)

    if filters.warehouse:
        # Keep whole entries, so harvesting still shows its input from the lake.
        row = frappe.qb.DocType("Stock Entry Detail").as_("row")
        in_warehouse = (
            frappe.qb.from_(row)
            .select(row.parent)
            .where((row.s_warehouse == filters.warehouse) | (row.t_warehouse == filters.warehouse))
        )
        query = query.where(se.name.isin(in_warehouse))

    return query.run(as_dict=True)


def get_data(filters):
    lines = {}

    for row in get_rows(filters):
        line = int(row.processing_line or 0)
        key = (str(row.posting_date), row.stock_entry_type, line)
        group = lines.setdefault(key, {"items": {}, "entries": set()})
        group["entries"].add(row.stock_entry)

        item = group["items"].setdefault(
            row.item_code, {"input_qty": 0.0, "output_qty": 0.0, "uom": row.uom}
        )
        # Repack rows are either consumed (source only) or produced (target only).
        if row.s_warehouse and not row.t_warehouse:
            item["input_qty"] += flt(row.qty)
        elif row.t_warehouse and not row.s_warehouse:
            item["output_qty"] += flt(row.qty)

    data = []
    for (posting_date, entry_type, line), group in lines.items():
        line_id = "{0}|{1}|{2}".format(posting_date, entry_type, line)
        input_qty = sum(i["input_qty"] for i in group["items"].values())
        output_qty = sum(i["output_qty"] for i in group["items"].values())

        data.append(
            {
                "id": line_id,
                "parent_id": None,
                "indent": 0,
                "posting_date": posting_date,
                "stock_entry_type": entry_type,
                "processing_line": line or None,
                "item_code": _("Line total") if line else _("No line set"),
                "input_qty": input_qty,
                "output_qty": output_qty,
                "yield_pct": (output_qty / input_qty * 100) if input_qty else None,
                "entries": len(group["entries"]),
            }
        )

        for item_code, item in sorted(group["items"].items()):
            data.append(
                {
                    "id": "{0}|{1}".format(line_id, item_code),
                    "parent_id": line_id,
                    "indent": 1,
                    "processing_line": line or None,
                    "item_code": item_code,
                    "input_qty": item["input_qty"],
                    "output_qty": item["output_qty"],
                    "uom": item["uom"],
                }
            )

    return data
