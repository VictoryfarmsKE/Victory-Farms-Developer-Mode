import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import flt

# List of asset categories that should be named by custom_asset_tag instead of naming_series
ASSET_TAG_CATEGORIES = [
    "Computer Equipment",
]


def autoname(doc, method):
    try:
        if doc.asset_category in ASSET_TAG_CATEGORIES:
            if doc.custom_asset_tag:
                # Check if an asset with this tag already exists
                if frappe.db.exists("Asset", doc.custom_asset_tag):
                    frappe.throw(
                        _("Asset Tag '{0}' already exists. Please use a unique Asset Tag.").format(doc.custom_asset_tag),
                        title=_("Duplicate Asset Tag")
                    )
                # Set the name to custom_asset_tag value
                doc.name = doc.custom_asset_tag
            else:
                frappe.throw(
                    _("Asset Tag is required for {0} category").format(doc.asset_category)
                )
        else:
            # For other categories, use the default naming_series
            if doc.naming_series:
                doc.name = make_autoname(doc.naming_series, doc=doc)
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Asset autoname Error")
        raise


def calculate_asset_value_from_purchase_receipt(doc, method):
    """
    Auto-calculate gross_purchase_amount from Purchase Receipt based on quantity.
    
    Formula: gross_purchase_amount = item_rate × asset_quantity
    
    This function is triggered on validate event of Asset doctype.
    It only runs when:
    - Asset is NOT an existing asset (is_existing_asset = 0)
    - Asset is NOT a composite asset
    - Purchase Receipt is linked
    - Item Code is specified
    """
    # Skip calculation for existing assets or composite assets
    if doc.is_existing_asset or doc.is_composite_asset:
        return
    
    # Skip if no purchase receipt linked
    if not doc.purchase_receipt:
        return
    
    # Skip if no item code
    if not doc.item_code:
        return
    
    try:
        # Get Purchase Receipt Item details
        pr_items = frappe.get_all(
            "Purchase Receipt Item",
            filters={
                "parent": doc.purchase_receipt,
                "item_code": doc.item_code,
                "is_fixed_asset": 1
            },
            fields=["base_net_rate", "rate", "base_net_amount", "qty", "name"]
        )
        
        if not pr_items:
            frappe.msgprint(
                _("No matching fixed asset item found in Purchase Receipt {0} for item {1}").format(
                    doc.purchase_receipt, doc.item_code
                ),
                indicator="orange",
                alert=True
            )
            return
        
        # Use the first matching item (or find exact match by qty if multiple)
        pr_item = None
        asset_qty = flt(doc.asset_quantity) or 1
        
        # Try to find exact match by quantity first
        for item in pr_items:
            if flt(item.qty) == asset_qty:
                pr_item = item
                break
        
        # If no exact match, use the first item
        if not pr_item:
            pr_item = pr_items[0]
        
        # Calculate gross_purchase_amount
        # Use base_net_rate (in company currency) for accuracy
        rate = flt(pr_item.base_net_rate) or flt(pr_item.rate)
        
        if rate > 0:
            calculated_amount = flt(rate * asset_qty, doc.precision("gross_purchase_amount"))
            
            # Only update if the value differs or is not set
            if not doc.gross_purchase_amount or flt(doc.gross_purchase_amount) != calculated_amount:
                old_value = doc.gross_purchase_amount
                doc.gross_purchase_amount = calculated_amount
                
                # Log the auto-calculation for audit trail
                frappe.msgprint(
                    _("Gross Purchase Amount auto-calculated: {0} (Rate: {1} × Qty: {2})").format(
                        frappe.format_value(calculated_amount, {"fieldtype": "Currency"}),
                        frappe.format_value(rate, {"fieldtype": "Currency"}),
                        asset_qty
                    ),
                    indicator="green",
                    alert=True
                )
                
                # Update total_asset_cost as well
                doc.total_asset_cost = flt(doc.gross_purchase_amount) + flt(doc.additional_asset_cost or 0)
        else:
            frappe.msgprint(
                _("Could not determine item rate from Purchase Receipt {0}").format(doc.purchase_receipt),
                indicator="orange",
                alert=True
            )
                
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Asset Value Auto-calculation Error for {0}").format(doc.name or "New Asset")
        )
        # Don't throw - allow the user to continue with manual entry
        frappe.msgprint(
            _("Could not auto-calculate asset value: {0}").format(str(e)),
            indicator="red",
            alert=True
        )
