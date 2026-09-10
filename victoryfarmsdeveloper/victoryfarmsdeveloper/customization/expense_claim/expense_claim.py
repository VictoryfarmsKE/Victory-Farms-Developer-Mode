import frappe
from frappe import _
from frappe.utils import today, getdate, add_months


VF_STAFF_ALLOWANCES_SUPPLIER = "VF Staff Allowances"
DEVELOPMENT_ALLOWANCE_COMPONENT = "Development Allowance"


def _has_development_allowance_rows(doc):
    """Return True if any expense row uses 'Development Allowance' claim type."""
    return any(
        row.expense_claim_type == DEVELOPMENT_ALLOWANCE_COMPONENT
        for row in (doc.expenses or [])
    )


def _get_sub_type(doc):
    """Return the first non-empty Expense Sub-Type from Development Allowance rows."""
    for row in (doc.expenses or []):
        if row.expense_claim_type == DEVELOPMENT_ALLOWANCE_COMPONENT and row.custom_expense_sub_type:
            return row.custom_expense_sub_type
    return None


def _is_any_row_taxable(doc):
    """Return True if any Development Allowance row has a taxable sub-type."""
    taxable_types = ("Personal Flights", "Other Taxable Expenses")
    return any(
        row.custom_expense_sub_type in taxable_types
        for row in (doc.expenses or [])
        if row.expense_claim_type == DEVELOPMENT_ALLOWANCE_COMPONENT
    )


def before_save_expense_claim(doc, method=None):
    """Prepare Development Allowance claims before saving.

    ERPNext requires payable_account on Expense Claim. For Development Allowance
    claims the actual reimbursement is done via Purchase Order or Additional
    Salary, so we auto-fill the company's default payable account to satisfy the
    validation without forcing the user to select one.
    """
    if not _has_development_allowance_rows(doc):
        return

    if not doc.payable_account:
        company = doc.company or frappe.defaults.get_user_default("Company")
        if company:
            payable_account = frappe.get_cached_value(
                "Company", company, "default_payable_account"
            )
            if payable_account:
                doc.payable_account = payable_account

    # Sync approval_status with the workflow state so ERPNext's standard
    # Expense Claim validation (which expects Approved/Rejected) does not block
    # the workflow Submit/Approve/Reject actions.
    if doc.workflow_state == "Rejected":
        doc.approval_status = "Rejected"
    elif doc.workflow_state in ("Submitted", "Approved"):
        doc.approval_status = "Approved"
    else:
        doc.approval_status = "Approved"


def before_submit_expense_claim(doc, method=None):
    """Enforce mandatory attachment and sub-type for Development Allowance rows."""
    if not _has_development_allowance_rows(doc):
        return

    if not frappe.db.exists(
        "File",
        {
            "attached_to_doctype": "Expense Claim",
            "attached_to_name": doc.name,
        },
    ):
        frappe.throw(_("Please attach supporting documents before submitting."))

    for row in (doc.expenses or []):
        if row.expense_claim_type == DEVELOPMENT_ALLOWANCE_COMPONENT and not row.custom_expense_sub_type:
            frappe.throw(
                _("Please select an Expense Sub-Type for row {0} (Development Allowance).").format(row.idx)
            )


def on_expense_claim_update(doc, method=None):
    """Handle Expense Claim workflow state changes for Development Allowance claims."""
    if not _has_development_allowance_rows(doc):
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
    if _is_any_row_taxable(doc):
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
                    "description": f"Development Allowance - {_get_sub_type(doc)} for {doc.employee_name}",
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
            "custom_note": doc.custom_hr_remarks or f"Development Allowance - {_get_sub_type(doc)}",
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

    Claims submitted between the 26th and 25th are processed in the
    current cycle — the payroll date is the actual submission date.
    Claims submitted after the 25th are pushed to the following cycle
    (1st of the next month).
    """
    submission_date = getdate(submission_date)
    cutoff_day = 25

    if submission_date.day > cutoff_day:
        # Push to next month (start of next cycle)
        next_month = add_months(submission_date, 1)
        return next_month.replace(day=1)

    # Within current cycle — keep the actual submission date
    return submission_date


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
        if _is_any_row_taxable(doc):
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
def get_designated_approver():
    """Return the designated Expense Claim approver (Payroll Officer).

    The approver is the enabled User with the Payroll Officer role.
    If multiple users have the role, prefer the one matching the
    configured email (Vincent Njuguna). Falls back to the first
    Payroll Officer found.
    """
    DESIGNATED_EMAIL = "vincentn@victoryfarmskenya.com"

    # Try the designated user first
    user = frappe.db.get_value(
        "User",
        {"email": DESIGNATED_EMAIL, "enabled": 1, "name": ["in", frappe.get_all("Has Role", filters={"role": "Payroll Officer"}, pluck="parent")]},
        "name",
    )
    if user:
        return user

    # Fallback: first enabled Payroll Officer
    user = frappe.db.sql(
        """
        SELECT u.name
        FROM `tabUser` u
        INNER JOIN `tabHas Role` r ON r.parent = u.name
        WHERE r.role = 'Payroll Officer'
            AND u.enabled = 1
        ORDER BY u.creation ASC
        LIMIT 1
        """,
        as_dict=True,
    )
    return user[0].name if user else None