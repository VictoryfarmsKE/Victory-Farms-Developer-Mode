import frappe


def get_notification_config():
    return {
        "for_doctype": {
            "Purchase Order": {
                "condition": "workflow_state IN ('To Approve', 'Pending Approval', 'Draft', 'To Amend') AND docstatus = 0"
            },
            "Leave Application": {
                "condition": "status IN ('Open', 'Pending Approval', 'Pending Sufficient Balance') AND docstatus = 0"
            },
            "Appraisal": {
                "condition": "workflow_state NOT IN ('Approved', 'Completed', 'Cancelled') AND docstatus = 0"
            },
            "Stock Entry": {
                "condition": "workflow_state IN ('Transfer Pending Confirmation-Driver', 'Transfer Confirmed by Driver') AND docstatus = 0"
            }
        }
    }
