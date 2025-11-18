# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import requests
import re


class Plot(Document):
	def validate(self):
		pass

	def before_save(self):
		link = getattr(self, "google_map_link", None)
		if not link:
			return
		try:
			coords = resolve_google_maps_link(link)
			if not coords:
				return
			lat, lng = coords.get("lat"), coords.get("lng")
			if not (lat and lng):
				return

			# Populate known coordinate fields if they exist on the DocType
			if hasattr(self, "latitude") and hasattr(self, "longitude"):
				self.latitude = lat
				self.longitude = lng
			else:
				if hasattr(self, "lat"):
					self.lat = lat
				if hasattr(self, "lng"):
					self.lng = lng
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Plot before_save map resolve failed")

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

