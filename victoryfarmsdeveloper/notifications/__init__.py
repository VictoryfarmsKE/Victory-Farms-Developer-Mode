import frappe

def get_notification_config():
    return {
        "for_doctype": {
            "Purchase Order": {
                "workflow_state": ["in", ["To Approve", "Pending Approval", "Draft", "To Amend"]],
                "docstatus": 0
            },
            "Leave Application": {
                "status": ["in", ["Open", "Pending Approval", "Pending Sufficient Balance"]],
                "docstatus": 0
            },
            "Appraisal": {
                "workflow_state": ["not in", ["Approved", "Completed", "Cancelled"]],
                "docstatus": 0
            },
            "Stock Entry": {
                "workflow_state": ["in", ["Transfer Pending Confirmation-Driver", "Transfer Confirmed by Driver"]],
                "docstatus": 0
            }
        }
    }
