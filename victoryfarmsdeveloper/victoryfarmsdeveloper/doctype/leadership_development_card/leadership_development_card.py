# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from victoryfarmsdeveloper.notifications import ldc

class EmployeeClearance(Document):
	def has_permission(doc, ptype, user):
		#Managers may view submitted LDCs of their direct reports (docstatus == 1)
		if "System Manager" in frappe.get_roles(user):
			return True

		employee = frappe.get_value("Employee", {"user_id": user}, "name")

		if employee and doc.employee == employee:
			return True
		if ptype == "read" and employee:
			if doc.docstatus == 1 and doc.reports_to:
				if doc.reports_to == employee:
					return True
		return False


	def get_permission_query_conditions(user):
		#SQL permission filter for list views.
		if not user:
			return ""
		full_access_roles = ["System Manager", "HR Manager"]
		if any(r in frappe.get_roles(user) for r in full_access_roles):
			return ""

		employee = frappe.get_value("Employee", {"user_id": user}, "name")
		if not employee:
			return "1=0"

		return f"((`tabLeadership Development Card`.employee = '{employee}') OR (`tabLeadership Development Card`.reports_to = '{employee}' AND `tabLeadership Development Card`.docstatus = 1))"

	def validate(self):
		#enforce minimum 30-word requirement
		min_fields = [
			"key_achievement",
			"biggest_challenge",
			"next_quarter_learning",
			"yearly_goal",
			"support_needed",
			"other_discussion_points",
		]

		for fn in min_fields:
			val = (self.get(fn) or "").strip()
			if not val:
				continue
			words = [w for w in val.split() if w]
			if len(words) < 30:
				frappe.throw(
					f"Field '{fn}' must be at least 30 words (currently {len(words)}).",
					title="Minimum Word Count",
				)

	def on_submit(self):
		#notify manager that the employee submitted their LDC
		try:
			ldc.notify_manager_on_submit(self)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "LDC: notify_manager_on_submit failed")

