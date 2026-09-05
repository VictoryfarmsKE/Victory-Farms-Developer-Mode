import frappe
from frappe import _
from frappe.utils import today, getdate, add_months


VF_STAFF_ALLOWANCES_SUPPLIER = "VF Staff Allowances"
DEVELOPMENT_ALLOWANCE_COMPONENT = "Development Allowance"


def validate_expense_claim(doc, method=None):
    """Sync approval_status with workflow_state so ERPNext's built-in
    Expense Claim validation does not block submission.

    ERPNext requires ``approval_status`` to be 'Approved' or 'Rejected'
    before the claim can be submitted.  When a Workflow is active the
    workflow_state controls the state, but the standard validation still
    checks approval_status — so we keep them in sync here.

    For Development Allowance claims the workflow controls the actual
    approval flow, so we always set approval_status to 'Approved' to
    prevent ERPNext's built-in check from blocking submission.
    """
    if doc.workflow_state == "Rejected":
        doc.approval_status = "Rejected"
    elif doc.workflow_state == "Approved":
        doc.approval_status = "Approved"
    elif doc.custom_claim_category == "Development Allowance":
        # Development Allowance uses a workflow — always pass the
        # standard ERPNext validation so the workflow Submit action works.
        doc.approval_status = "Approved"
    elif doc.workflow_state == "Submitted":
        doc.approval_status = "Approved"


def on_expense_claim_update(doc, method=None):
    """Handle Expense Claim workflow state changes for Development Allowance claims."""
    if doc.custom_claim_category != "Development Allowance":
        return

    if not doc.workflow_state:
        return

    previous_workflow_state = doc.get_doc_before_save().workflow_state if doc.get_doc_before_save() else None

    if doc.workflow_state == previous_workflow_state:
        return

    if doc.workflow_state == "Approved":
        handle_approved_claim(doc)
        send_status_notification(doc, "approved")
    elif doc.workflow_state == "Rejected":
        send_status_notification(doc, "rejected")


def handle_approved_claim(doc):
    """Create Purchase Order or Additional Salary based on expense sub-type."""
    if doc.custom_is_taxable:
        create_additional_salary(doc)
    else:
        create_purchase_order(doc)


def create_purchase_order(doc):
    """Create a Purchase Order for non-taxable Development Allowance claims."""
    if frappe.db.exists("Purchase Order", {"custom_expense_claim": doc.name}):
        return

    supplier = get_or_create_supplier()
    company = doc.company or frappe.defaults.get_user_default("Company")

    po = frappe.get_doc(
        {
            "doctype": "Purchase Order",
            "supplier": supplier,
            "company": company,
            "transaction_date": today(),
            "custom_expense_claim": doc.name,
            "items": [
                {
                    "item_code": get_default_service_item(),
                    "schedule_date": today(),
                    "description": f"Development Allowance - {doc.custom_expense_sub_type} for {doc.employee_name}",
                    "qty": 1,
                    "rate": doc.total_sanctioned_amount or doc.total_claimed_amount,
                    "amount": doc.total_sanctioned_amount or doc.total_claimed_amount,
                }
            ],
        }
    )
    po.insert(ignore_permissions=True)
    po.save()

    frappe.msgprint(
        _(
            "Purchase Order {0} created for Expense Claim {1}."
        ).format(po.name, doc.name),
        alert=True,
    )


def create_additional_salary(doc):
    """Create an Additional Salary draft for taxable Development Allowance claims."""
    if frappe.db.exists("Additional Salary", {"custom_expense_claim": doc.name}):
        return

    payroll_date = get_payroll_date(doc.posting_date or today())

    additional_salary = frappe.get_doc(
        {
            "doctype": "Additional Salary",
            "employee": doc.employee,
            "salary_component": DEVELOPMENT_ALLOWANCE_COMPONENT,
            "amount": doc.total_sanctioned_amount or doc.total_claimed_amount,
            "payroll_date": payroll_date,
            "company": doc.company or frappe.defaults.get_user_default("Company"),
            "custom_expense_claim": doc.name,
            "custom_note": doc.custom_hr_remarks or f"Development Allowance - {doc.custom_expense_sub_type}",
            "docstatus": 0,
        }
    )
    additional_salary.insert(ignore_permissions=True)
    additional_salary.save()

    frappe.msgprint(
        _(
            "Additional Salary {0} created as draft for Expense Claim {1}. Payroll date: {2}."
        ).format(additional_salary.name, doc.name, payroll_date),
        alert=True,
    )


def get_payroll_date(submission_date):
    """Return the payroll date based on the 26th-25th cycle rule.

    Claims submitted between the 26th and 25th are processed in the current cycle.
    Claims submitted after the 25th are pushed to the following cycle.
    """
    submission_date = getdate(submission_date)
    cutoff_day = 25

    if submission_date.day > cutoff_day:
        # Push to next month
        next_month = add_months(submission_date, 1)
        return next_month.replace(day=1)

    return submission_date.replace(day=1)


def send_status_notification(doc, status):
    """Send email notification to the requester when claim is approved or rejected."""
    employee_email = frappe.db.get_value("Employee", doc.employee, "prefered_email")
    if not employee_email:
        return

    subject = f"Development Allowance Claim {status.title()}: {doc.name}"
    message = f"""
    <p>Dear {doc.employee_name},</p>
    <p>Your Development Allowance claim <strong>{doc.name}</strong> has been <strong>{status}</strong>.</p>
    """

    if status == "approved":
        if doc.custom_is_taxable:
            message += f"""
            <p>An Additional Salary draft has been created for payroll processing.</p>
            """
        else:
            message += f"""
            <p>A Purchase Order has been created for reimbursement.</p>
            """

    if doc.custom_hr_remarks:
        message += f"""
        <p><strong>HR Remarks:</strong> {doc.custom_hr_remarks}</p>
        """

    message += "<p>Best regards,<br>HR Team</p>"

    frappe.sendmail(
        recipients=[employee_email],
        subject=subject,
        message=message,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
    )


def get_or_create_supplier():
    """Return the VF Staff Allowances supplier, creating it if necessary."""
    if frappe.db.exists("Supplier", VF_STAFF_ALLOWANCES_SUPPLIER):
        return VF_STAFF_ALLOWANCES_SUPPLIER

    supplier = frappe.get_doc(
        {
            "doctype": "Supplier",
            "supplier_name": VF_STAFF_ALLOWANCES_SUPPLIER,
            "supplier_type": "Company",
            "country": "Kenya",
        }
    )
    supplier.insert(ignore_permissions=True)
    return supplier.name


def get_default_service_item():
    """Return a default service item for Purchase Orders."""
    item_code = "Development Allowance Service"
    if frappe.db.exists("Item", item_code):
        return item_code

    item = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": "Development Allowance Service",
            "item_group": "Services",
            "stock_uom": "Nos",
            "is_stock_item": 0,
        }
    )
    item.insert(ignore_permissions=True)
    return item.name


@frappe.whitelist()
def get_payroll_officer_user():
    """Return the first enabled User with the Payroll Officer role.

    Roles live in the ``Has Role`` child table, so a direct ``get_list``
    filter on ``roles`` is not valid. Query the join instead.
    """
    user = frappe.db.sql(
        """
        SELECT u.name
        FROM `tabUser` u
        INNER JOIN `tabHas Role` r ON r.parent = u.name
        WHERE r.role = 'Payroll Officer'
            AND u.enabled = 1
        ORDER BY u.creation DESC
        LIMIT 1
        """,
        as_dict=True,
    )
    return user[0].name if user else None
