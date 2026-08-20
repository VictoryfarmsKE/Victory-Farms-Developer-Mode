"""
Frappe Console Script — Export All Enabled Warehouses for Victory Farms Ltd
Paste this into ERPNext System Console (/app/system-console) and run.

Outputs a CSV of all warehouses that are:
- NOT disabled (disabled = 0)
- NOT group parents (is_group = 0)
- Belong to company "Victory Farms Ltd"

NOTE: Do NOT use "import frappe" — frappe is already available in System Console.
"""

warehouses = frappe.db.get_all(
    "Warehouse",
    filters={
        "company": "Victory Farms Ltd",
        "disabled": 0,
        "is_group": 0,
    },
    fields=["name", "warehouse_name", "parent_warehouse", "warehouse_type", "creation", "modified"],
    order_by="name asc",
)

csv_lines = ["Name,Warehouse Name,Parent Warehouse,Warehouse Type,Created,Last Modified"]
for wh in warehouses:
    csv_lines.append('"{}","{}","{}","{}","{}","{}"'.format(
        wh["name"], wh.get("warehouse_name", ""), wh.get("parent_warehouse", ""),
        wh.get("warehouse_type", ""), wh["creation"], wh["modified"]
    ))

print("\n".join(csv_lines))
print("\n\n=== TOTAL ENABLED WAREHOUSES: {} ===".format(len(warehouses)))
