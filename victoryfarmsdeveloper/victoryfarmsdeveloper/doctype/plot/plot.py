# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import requests
import re


class Plot(Document):
    def validate(self):
        pass

@frappe.whitelist()  
def resolve_google_maps_link(short_url):
	try:
		response = requests.head(short_url, allow_redirects=True, timeout=5)
		final_url = response.url
		match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
		if match:
			return {"lat": match.group(1), "lng": match.group(2)}
		else:
			return {}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Google Maps Resolve Error")
		return {}


def before_save(self):
    resolve_google_maps_link(self.google_map_link)
