import frappe


def execute():
    """Pre-populate the Pond DocType with the 8 known ponds and their hapa counts."""
    ponds = [
        {"pond_name": "B11", "number_of_hapas": 15},
        {"pond_name": "H1-02", "number_of_hapas": 15},
        {"pond_name": "B8", "number_of_hapas": 16},
        {"pond_name": "H0-07", "number_of_hapas": 18},
        {"pond_name": "H2-07", "number_of_hapas": 4},
        {"pond_name": "H2-04", "number_of_hapas": 10},
        {"pond_name": "H2-06", "number_of_hapas": 9},
        {"pond_name": "H0-10", "number_of_hapas": 17},
    ]

    for p in ponds:
        if not frappe.db.exists("Pond", p["pond_name"]):
            doc = frappe.get_doc({
                "doctype": "Pond",
                "pond_name": p["pond_name"],
                "number_of_hapas": p["number_of_hapas"],
            })
            doc.insert(ignore_permissions=True)
