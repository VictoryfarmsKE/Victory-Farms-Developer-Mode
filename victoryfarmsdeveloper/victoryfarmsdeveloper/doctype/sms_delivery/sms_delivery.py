import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class SMSDelivery(Document):
	@staticmethod
	def clear_old_logs(days=30):
		table = frappe.qb.DocType("SMS Delivery")
		frappe.db.delete(
			table,
			filters=(table.status == "Sent") & (table.modified < (Now() - Interval(days=days))),
		)
