# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class TalentPool(Document):
	def before_save(self):
		if self.surname:
			self.full_name = f"{self.first_name} {self.surname}"
		elif self.middle_name:
			self.full_name = f"{self.first_name} {self.middle_name}"
		else:
			self.full_name = self.first_name

