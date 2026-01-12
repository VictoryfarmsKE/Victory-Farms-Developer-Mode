# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

"""
Multiple Half Days Feature - Setup Script
==========================================

Run this script to set up the Multiple Half Days feature:
    bench execute victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.setup.setup_multiple_half_days

Or use the individual functions as needed.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_multiple_half_days():
    """
    Main setup function for Multiple Half Days feature.
    
    This function:
    1. Creates the Leave Application Half Day child DocType (if not exists)
    2. Adds the half_day_dates custom field to Leave Application
    """
    print("Setting up Multiple Half Days feature...")
    
    # Step 1: Ensure DocType exists
    ensure_child_doctype_exists()
    
    # Step 2: Create custom field
    create_half_day_dates_field()
    
    # Step 3: Clear cache
    frappe.clear_cache()
    
    print("✅ Multiple Half Days feature setup complete!")
    print("")
    print("Next steps:")
    print("1. Run 'bench build' to compile JS assets")
    print("2. Reload the browser")
    print("3. Open Leave Application to test the feature")


def ensure_child_doctype_exists():
    """Ensure the Leave Application Half Day DocType exists"""
    if frappe.db.exists("DocType", "Leave Application Half Day"):
        print("  ✓ DocType 'Leave Application Half Day' already exists")
        return
    
    print("  Creating DocType 'Leave Application Half Day'...")
    
    # The DocType should already exist from the JSON file
    # This is a fallback to create it programmatically if needed
    doc = frappe.new_doc("DocType")
    doc.update({
        "name": "Leave Application Half Day",
        "module": "VictoryFarmsDeveloper",
        "istable": 1,
        "editable_grid": 1,
        "track_changes": 1,
        "fields": [
            {
                "fieldname": "half_day_date",
                "fieldtype": "Date",
                "label": "Half Day Date",
                "reqd": 1,
                "in_list_view": 1,
            }
        ]
    })
    doc.insert(ignore_permissions=True)
    print("  ✓ DocType 'Leave Application Half Day' created")


def create_half_day_dates_field():
    """Create the half_day_dates custom field on Leave Application"""
    
    custom_fields = {
        "Leave Application": [
            {
                "fieldname": "half_day_dates",
                "label": "Half Day Dates",
                "fieldtype": "Table",
                "options": "Leave Application Half Day",
                "insert_after": "half_day_date",
                "depends_on": "eval:doc.half_day && doc.from_date && doc.to_date",
                "description": "Select multiple dates as half days. Each half day reduces leave by 0.5 days.",
            }
        ]
    }
    
    print("  Creating custom field 'half_day_dates'...")
    create_custom_fields(custom_fields, update=True)
    print("  ✓ Custom field 'half_day_dates' created")


def remove_multiple_half_days():
    """
    Remove the Multiple Half Days feature.
    
    Use this to clean up if you want to remove the feature.
    
    Run with:
        bench execute victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.setup.remove_multiple_half_days
    """
    print("Removing Multiple Half Days feature...")
    
    # Remove custom field
    if frappe.db.exists("Custom Field", "Leave Application-half_day_dates"):
        frappe.delete_doc("Custom Field", "Leave Application-half_day_dates")
        print("  ✓ Custom field removed")
    
    # Note: We don't remove the DocType as it may have data
    # If you want to remove it completely, uncomment below:
    # if frappe.db.exists("DocType", "Leave Application Half Day"):
    #     frappe.delete_doc("DocType", "Leave Application Half Day", force=True)
    #     print("  ✓ DocType removed")
    
    frappe.clear_cache()
    print("✅ Multiple Half Days feature removed!")


def migrate_existing_half_days():
    """
    Migrate existing single half_day_date values to the new half_day_dates table.
    
    Run with:
        bench execute victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.setup.migrate_existing_half_days
    """
    print("Migrating existing half day dates...")
    
    # Find all leave applications with half_day_date set
    applications = frappe.get_all(
        "Leave Application",
        filters={
            "half_day": 1,
            "half_day_date": ["is", "set"],
        },
        fields=["name", "half_day_date"]
    )
    
    migrated = 0
    for app in applications:
        # Check if already has entries in child table
        existing = frappe.db.count(
            "Leave Application Half Day",
            filters={"parent": app.name}
        )
        
        if existing == 0:
            # Create entry in child table
            doc = frappe.get_doc("Leave Application", app.name)
            doc.append("half_day_dates", {
                "half_day_date": app.half_day_date
            })
            doc.save(ignore_permissions=True)
            migrated += 1
    
    print(f"  ✓ Migrated {migrated} leave applications")
    frappe.db.commit()
    print("✅ Migration complete!")


if __name__ == "__main__":
    setup_multiple_half_days()
