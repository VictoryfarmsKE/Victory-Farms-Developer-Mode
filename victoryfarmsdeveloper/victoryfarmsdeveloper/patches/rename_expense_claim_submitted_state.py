import frappe

OLD_STATE = "Submitted"
NEW_STATE = "Pending Approval (Payroll Officer)"


def execute():
    """Rename the Expense Claim workflow's "Submitted" state to the pending-approval state.

    The workflow lives in each site's database, so this keeps live, pre-prod and
    test identical without editing the workflow by hand. Safe to run twice.
    """
    if not frappe.db.exists("Workflow State", NEW_STATE):
        frappe.get_doc(
            {"doctype": "Workflow State", "workflow_state_name": NEW_STATE, "style": "Warning"}
        ).insert(ignore_permissions=True)

    for name in frappe.get_all("Workflow", filters={"document_type": "Expense Claim"}, pluck="name"):
        workflow = frappe.get_doc("Workflow", name)
        changed = False
        for row in workflow.states:
            if row.state == OLD_STATE:
                row.state = NEW_STATE
                changed = True
        for row in workflow.transitions:
            if row.state == OLD_STATE:
                row.state = NEW_STATE
                changed = True
            if row.next_state == OLD_STATE:
                row.next_state = NEW_STATE
                changed = True
        if changed:
            workflow.save(ignore_permissions=True)

    frappe.db.sql(
        "update `tabExpense Claim` set workflow_state = %s where workflow_state = %s",
        (NEW_STATE, OLD_STATE),
    )
