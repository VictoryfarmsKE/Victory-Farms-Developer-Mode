import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, now_datetime

TRANSIT_WAREHOUSE_TYPE = "Transit"


class WeighbridgeReading(Document):
	def validate(self):
		self.set_defaults()
		self.validate_truck()
		self.validate_weight()
		self.validate_reading_time()

	def set_defaults(self):
		if not self.reading_time:
			self.reading_time = now_datetime()

		if not self.recorded_by:
			self.recorded_by = frappe.session.user

	def validate_truck(self):
		warehouse_type = frappe.db.get_value("Warehouse", self.truck, "warehouse_type")

		if warehouse_type != TRANSIT_WAREHOUSE_TYPE:
			frappe.throw(
				_("{0} is not a truck. Pick a warehouse whose Warehouse Type is {1}.").format(
					frappe.bold(self.truck), frappe.bold(TRANSIT_WAREHOUSE_TYPE)
				)
			)

	def validate_weight(self):
		if flt(self.weight) <= 0:
			frappe.throw(_("Weight must be greater than zero."))

	def validate_reading_time(self):
		if get_datetime(self.reading_time) > now_datetime():
			frappe.throw(_("Reading Time cannot be in the future."))

	def on_submit(self):
		if self.reading_type == "Gross":
			self.warn_if_lighter_than_tare()

	def warn_if_lighter_than_tare(self):
		tare = frappe.db.sql(
			"""
			select name, weight
			from `tabWeighbridge Reading`
			where truck = %(truck)s
				and reading_type = 'Tare'
				and docstatus = 1
				and reading_time <= %(reading_time)s
			order by reading_time desc
			limit 1
			""",
			{"truck": self.truck, "reading_time": self.reading_time},
			as_dict=True,
		)

		if tare and flt(self.weight) < flt(tare[0].weight):
			frappe.msgprint(
				_("This loaded weight is lighter than the empty weight recorded in {0}. Please check the reading.").format(
					frappe.bold(tare[0].name)
				),
				title=_("Check the reading"),
				indicator="orange",
			)
