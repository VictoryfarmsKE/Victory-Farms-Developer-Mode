# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from victoryfarmsdeveloper.notifications import ldc


class LeadershipDevelopmentCard(Document):
	def validate(self):
		#enforce minimum 30-word requirement
		min_fields = [
			"key_achievement",
			"biggest_challenge",
			"next_quarter_learning",
			"yearly_goal",
			"support_needed",
			"other_discussion_points",
			"extra_feedback",
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
	#ensure all fields are filled out before allowing submission	
	def before_submit(self):
		required_fields = [
			"key_achievement",
			"biggest_challenge",
			"next_quarter_learning",
			"yearly_goal",
			"support_needed",
			"other_discussion_points",
			"extra_feedback",
		]

		for fn in required_fields:
			val = (self.get(fn) or "").strip()
			if not val:
				frappe.throw(
					f"All fields (except optional ones) are required before submitting.",
					title="Missing Required Field",
				)
 
	def on_submit(self):
		#notify manager that the employee submitted their LDC
		try:
			ldc.notify_manager_on_submit(self)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "LDC: notify_manager_on_submit failed")
