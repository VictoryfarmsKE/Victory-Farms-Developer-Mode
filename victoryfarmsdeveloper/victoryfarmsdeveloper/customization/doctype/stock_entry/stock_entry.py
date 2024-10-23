import frappe
import erpnext
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
import json

class CustomStockEntry(StockEntry):
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

    @frappe.whitelist()
    def update_child_table(self):
        self.custom_crates = []
        # self.save()
        self.adjust_crates()

    def adjust_crates(self):
        items_dict = {}
        if self.items:
            for item in self.items:
                if not item.get("item_code") in items_dict.keys():
                    items_dict[item.get("item_code")] = {}

                items_dict[item.get("item_code")] = {
                    "item_code": item.get("item_code"),
                    "qty": item.get("qty"),
                    "uom": item.get("uom"),
                }
        self.convert_to_crates(items_dict)

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
                    'crate_number': crate['crate_number'],
                    'uom': crate['uom'],
                    'qty': crate['qty'],
                    # 'crate_type': crate['crate_type']
                })

            # frappe.log("Crate List: {}".format(json.dumps(crate_list))) 
            # self.save()

    def on_submit(self):
        if not self.custom_crates:
            frappe.throw("Crates table is mandatory!")

        self.validate_crates()
