import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from frappe import _
from erpnext.stock.doctype.stock_entry.stock_entry import make_stock_in_entry as original_make_stock_in_entry
from frappe.utils import nowdate


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
        self.process_items_in_batches(items_dict)

    def process_items_in_batches(self, items_dict, batch_size=10):
        items_list = list(items_dict.items())
        for i in range(0, len(items_list), batch_size):
            batch = items_list[i:i + batch_size]
            frappe.enqueue(self.convert_to_crates, items_batch=batch, queue='long', timeout=5000)
        
    def convert_to_crates(self, items_batch):
        items_dict = dict(items_batch)
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
            full_crates = int(total_qty // 25)  # Calculate full crates (25 kgs per crate)
            remaining_qty = total_qty % 25  # Calculate remaining quantity for half crate

            # Create entries for each full crate
            for _ in range(full_crates):
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
            
@frappe.whitelist()
def make_stock_in_entry(source_name, target_doc=None):
    # Check if a stock entry has already been created for this source
    existing_entry = frappe.db.exists(
        "Stock Entry",
        {
            "outgoing_stock_entry": source_name,
            "docstatus": ["!=", 2],  # Exclude cancelled entries
        },
    )
    if existing_entry:
        # Throw an exception to stop further execution
        frappe.throw(
            _('A Stock Entry has already been created for this transaction: Click <a href="/app/stock-entry/{0}" target="_blank">{0}</a> to go to the created stock entry').format(existing_entry),
            title=_("Duplicate Stock Entry")
        )

    # Call the original function if no duplicate exists
    return original_make_stock_in_entry(source_name, target_doc)

def before_save_stock_entry(doc, method):
        #Get previous workflow state
        previous_doc = doc.get_doc_before_save()
        previous_state = previous_doc.workflow_state if previous_doc else None
        if (
            doc.stock_entry_type == "Material Transfer"
            and doc.items
            and all(item.item_group in ["Gutted Fish-Tilapia", "Crates", "Packaging"] for item in doc.items)
            and any(item.item_group == "Gutted Fish-Tilapia" for item in doc.items)
            and doc.destination_warehouse_type in ["Branch", "LC"]
            and doc.from_warehouse_type == "LC"
        ):
          if previous_state != "Transfer Pending Confirmation-Driver" and doc.workflow_state == "Transfer Pending Confirmation-Driver":
                # Auto-create CoA if workflow state is "Transfer Pending Confirmation - Driver"
                if not frappe.db.exists("Certificate of Analysis", {"stock_entry_reference": doc.name}):
                    coa = frappe.new_doc("Certificate of Analysis")
                    coa.stock_entry_reference = doc.name
                    coa.dispatch_date = nowdate()
                    coa.destination = doc.destination_warehouse
                    coa.truck_driver = doc.driver
                    coa.insert()
                    frappe.msgprint(_("A Certificate of Analysis has been created. Please complete and submit it."))
                    coa.save()
                else:
                    frappe.msgprint(_("A Certificate of Analysis already exists for this Stock Entry. Please complete and submit it."))
                    
def before_submit_stock_entry(doc, method):
    #Get previous workflow state
    previous_doc = doc.get_doc_before_save()
    previous_state = previous_doc.workflow_state if previous_doc else None
    if (
            doc.stock_entry_type == "Material Transfer"
            and doc.items
            and all(item.item_group in ["Gutted Fish-Tilapia", "Crates", "Packaging"] for item in doc.items)
            and any(item.item_group == "Gutted Fish-Tilapia" for item in doc.items)
            and doc.destination_warehouse_type in ["Branch", "LC"]
            and doc.from_warehouse_type == "LC"
        ):
        if previous_state != "Transfer Confirmed by Driver" and doc.workflow_state == "Transfer Confirmed by Driver":
        # Prevent final confirmation without submitted CoA
            submitted_coa = frappe.get_all("Certificate of Analysis", {
                "stock_entry_reference": doc.name,
                "docstatus": 1
            })
            if not submitted_coa:
                frappe.throw(_("You must submit the Certificate of Analysis before confirming this Stock Entry."))
