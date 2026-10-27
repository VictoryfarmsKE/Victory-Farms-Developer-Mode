from frappe.model.document import Document

from victoryfarmsdeveloper.setup.report_exports import clear_background_reports


class ReportExportSettings(Document):
	def on_update(self):
		clear_background_reports()
