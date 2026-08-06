def get_dashboard_data_for_purchase_invoice(data):
    data["transactions"].append({
        "label": "Travel",
        "items": ["Travel Allowance Claim"]
    })
    data["internal_links"]["Travel Allowance Claim"] = \
        ["Purchase Invoice", "custom_travel_allowance_claim"]
    return data


def get_dashboard_data_for_travel_allowance_claim(data):
    data["transactions"].append({
        "label": "Finance",
        "items": ["Purchase Invoice"]
    })
    data["internal_links"]["Purchase Invoice"] = \
        ["Purchase Invoice", "custom_travel_allowance_claim"]
    return data
