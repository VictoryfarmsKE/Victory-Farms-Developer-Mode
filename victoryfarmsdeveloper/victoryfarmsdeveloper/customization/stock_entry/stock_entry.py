import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
import json
from frappe import _

class CustomStockEntry(StockEntry):
    @frappe.whitelist()
    def update_crates(self):
        self.custom_crates = []
        self.save()
        self.adjust_crates()
        
    def validate_crates(self):
        items = self.get_items()
        custom_crates = self.get_crates()
        
        for i, q in items.items():
            for c, cq in custom_crates.items():
                if i == c:
                    if not q == cq:
                        frappe.throw("Quantity {} for {} does not match quantity of {} in crates!".format(q,i,cq))
        
    def get_items(self):
        items = {}
        # Assuming 'sku_summary' is the fieldname for the child table
        if self.sku_summary:
            for item in self.sku_summary:
                item_code = item.get("item_code")
                qty = item.get("qty")
                items[item_code] = items.get(item_code, 0) + qty
        
        return items

    def get_crates(self):
        custom_crates = {}
        # Assuming 'crates' is the fieldname for the crate child table
        if self.custom_crates:
            for crate in self.custom_crates:
                item_code = crate.get("item_code")
                custom_crates[item_code] = custom_crates.get(item_code, 0) + crate.get("qty")
        return custom_crates

    def adjust_crates(self):
        items_dict = {}
        if self.items:
            for item in self.items:
                item_code = item.get("item_code")
                if item_code == "Crates":
                    continue  # Skip items with item_code "Crates"
                
                if item_code not in items_dict:
                    items_dict[item_code] = {}

                items_dict[item_code] = {
                    "item_code": item_code,
                    "qty": item.get("qty"),
                    "uom": item.get("uom"),
                }
        self.enqueue_convert_to_crates(items_dict)
        self.convert_to_crates(items_dict)
  
    def enqueue_convert_to_crates(self, items_dict):
        frappe.enqueue('victoryfarmsdeveloper.victoryfarmsdeveloper.customization.stock_entry.stock_entry.CustomStockEntry.convert_to_crates', items_dict=items_dict)

    def convert_to_crates(self, items_dict):
        for key, value in items_dict.items():
            conv_factor = frappe.db.get_value(
                "UOM Conversion Factor",
                {"category": "Mass", "from_uom": value.get("uom"), "to_uom": "Crate"},
                "value",
            )
            value["crates_qty"] = value["qty"] * conv_factor

            value["full_crate_qty"] = value["crates_qty"] // 1
            value["half_crate_qty"] = value["crates_qty"] % 1

        # List to store the new entries
        crate_list = []

        # Initialize a global crate number
        global_crate_number = 1
        
        # Loop through each item in the dictionary
        for item_name, details in items_dict.items():
            total_qty = details["qty"]
            full_crates = int(
                total_qty // 25
            )  # Calculate full crates (25 kgs per crate)
            remaining_qty = (
                total_qty % 25
            )  # Calculate remaining quantity for half crate

            # Create entries for each full crate
            for i in range(full_crates):
                crate_entry = {
                    "item_code": details["item_code"],
                    "crate_number": global_crate_number,
                    "uom": details["uom"],
                    "qty": 25,  # Each full crate holds 25 kgs
                    "crate_type": "Full Crate",
                }
                crate_list.append(crate_entry)
                global_crate_number += 1  # Increment the global crate number
                
            # If there is remaining quantity (half crate), add that as well
            if remaining_qty > 0:
                crate_entry = {
                    "item_code": details["item_code"],
                    "crate_number": global_crate_number,
                    "uom": details["uom"],
                    "qty": remaining_qty,  # Remaining quantity for half crate
                    "crate_type": "Half Crate",
                }
                crate_list.append(crate_entry)
                global_crate_number += 1  # Increment the global crate number             
        self.append_crates(crate_list)

    def append_crates(self, crate_list):
        for crate in crate_list:
            # Check if the crate already exists
            existing_crate = next((c for c in self.custom_crates if c.item_code == crate['item_code'] and c.crate_number == crate['crate_number']), None)

            if existing_crate:
                # If the crate exists, update the quantity
                existing_crate.qty = crate['qty']
            else:
                # If the crate does not exist, create a new entry
                self.append("custom_crates", {
                    'item_code': crate['item_code'],
                    # 'crate_number': crate['crate_number'],
                    'uom': crate['uom'],
                    'qty': crate['qty'],
                })
            self.append_total_crates(crate_list)
            
    def append_total_crates(self, crate_list):
        aggregated_crates = {}
        for crate in crate_list:
            item_code = crate['item_code']
            if item_code not in aggregated_crates:
                aggregated_crates[item_code] = {
                    "total_full_crates": 0,
                    "total_half_crates": 0,
                }

            if crate['crate_type'] == "Full Crate":
                aggregated_crates[item_code]["total_full_crates"] += 1
            else:
                aggregated_crates[item_code]["total_half_crates"] += 1

        # Create a list to store aggregated results to be appended to the table
        aggregated_results = []
        for item_code, counts in aggregated_crates.items():
            total_crates = counts["total_full_crates"] + counts["total_half_crates"]
            aggregated_results.append({
                "item_code": item_code,
                "total_full_crates": counts["total_full_crates"],
                "total_half_crates": counts["total_half_crates"],
                "total_crates": total_crates,
            })
        for crates in aggregated_results:
            # Check if the crate already exists
            existing_crate = next((c for c in self.custom_total_crates if c.item_code == crates['item_code'] and c.total_crates == crates['total_crates']), None)

            if existing_crate:
                # If the crate exists, update the quantity
                existing_crate.total_crates = crates['total_crates']
            else:
                # If the crate does not exist, create a new entry
                 self.append("custom_total_crates", {
                    'item_code': crates['item_code'],
                    'total_crates': crates['total_crates'],
                })
            self.custom_number_of_crates = sum(crates['total_crates'] for crates in aggregated_results)
            self.save()
            
                         
            
# def on_submit(self, method):
#     if not self.custom_crates:
#         frappe.throw("Crates table is mandatory!")

