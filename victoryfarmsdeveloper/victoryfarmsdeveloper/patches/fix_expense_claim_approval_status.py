import frappe

PENDING_STATES = ("Pending Approval (Payroll Officer)", "Submitted")


def execute():
    """Align HRMS approval_status/status with each submitted claim's workflow state.

    Claims awaiting a decision had been marked "Approved" at submission, so HRMS
    dashboards counted them as approved and treated them as payable. Rejected
    claims kept "Approved" because Frappe skips validate for post-submit
    workflow transitions. Sanctioned amounts are left untouched so cancelling a
    claim still reverses its accounting entry. Safe to run twice.
    """
    frappe.db.sql(
        """
        update `tabExpense Claim`
        set approval_status = 'Draft', status = 'Submitted'
        where docstatus = 1
          and workflow_state in %(states)s
          and ifnull(total_amount_reimbursed, 0) = 0
        """,
        {"states": PENDING_STATES},
    )
    frappe.db.sql(
        """
        update `tabExpense Claim`
        set approval_status = 'Approved'
        where docstatus = 1 and workflow_state = 'Approved'
        """
    )
    frappe.db.sql(
        """
        update `tabExpense Claim`
        set approval_status = 'Rejected', status = 'Rejected'
        where docstatus = 1 and workflow_state = 'Rejected'
        """
    )
