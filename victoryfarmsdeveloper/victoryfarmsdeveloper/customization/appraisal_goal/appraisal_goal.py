import frappe
from frappe.model.document import Document

class CustomAppraisalGoal(Document):
    def onload(self):
        kra_doc = frappe.get_doc("KRA", self.kra)
    
        self.custom_did_the_employee = kra_doc.description
        
        self.save()