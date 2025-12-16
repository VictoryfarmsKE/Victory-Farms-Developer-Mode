import frappe
from frappe import _
from frappe.model.naming import make_autoname

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
