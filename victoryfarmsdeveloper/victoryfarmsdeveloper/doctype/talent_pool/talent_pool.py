# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe
import os
from frappe.model.document import Document

class TalentPool(Document):
	def before_save(self):
		if self.surname:
			self.full_name = f"{self.first_name} {self.surname}"
		elif self.middle_name:
			self.full_name = f"{self.first_name} {self.middle_name}"
		else:
			self.full_name = self.first_name
   #validate unique email address for every talent pool entry
	def validate(self):
		if self.email:
			existing_entry = frappe.db.exists("Talent Pool", {"email": self.email, "name": ["!=", self.name]})
			if existing_entry:
				frappe.throw(f"Email {self.email} is already used in another talent pool entry.")
		
		# Ensure the file is in pdf format
		if self.resume and not self.resume.endswith('.pdf'):
			frappe.throw("Resume must be in PDF format.")