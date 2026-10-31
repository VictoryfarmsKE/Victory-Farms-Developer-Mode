import frappe
from frappe import _
from frappe.utils import today, getdate, add_months, get_url_to_form, fmt_money, formatdate, escape_html


VF_STAFF_ALLOWANCES_SUPPLIER = "VF Staff Allowances"
DEVELOPMENT_ALLOWANCE_COMPONENT = "Development Allowance"


def _has_development_allowance_rows(doc):
    """Return True if any expense row uses 'Development Allowance' claim type."""
    return any(
        row.expense_type == DEVELOPMENT_ALLOWANCE_COMPONENT
        for row in (doc.expenses or [])
    )


def _get_sub_type(doc):
    """Return the first non-empty Expense Sub-Type from Development Allowance rows."""
    for row in (doc.expenses or []):
        if row.expense_type == DEVELOPMENT_ALLOWANCE_COMPONENT and row.custom_expense_sub_type:
            return row.custom_expense_sub_type
    return None


def _is_any_row_taxable(doc):
    """Return True if any Development Allowance row has a taxable sub-type."""
    return any(
        "(Taxable)" in (row.custom_expense_sub_type or "")
        for row in (doc.expenses or [])
        if row.expense_type == DEVELOPMENT_ALLOWANCE_COMPONENT
    )


EXPENSE_CLAIM_PRIVILEGED_ROLES = ("HR Manager", "Expense Approver", "System Manager")


def _enforce_own_claim(doc):
    """Restrict employees to filing expense claims only for themselves.

    Users with privileged HR roles may file on behalf of other employees.
    Everyone else must file against the Employee record linked to their
    own user account.
    """
    if doc.is_new() is False:
        return

    if set(frappe.get_roles(frappe.session.user)) & set(EXPENSE_CLAIM_PRIVILEGED_ROLES):
        return

    own_employee = frappe.db.get_value(
        "Employee", {"user_id": frappe.session.user}, "name"
    )
    if own_employee and doc.employee != own_employee:
        frappe.throw(
            _("You can only create an expense claim for yourself ({0}).").format(own_employee)
        )


def validate_expense_claim(doc, method=None):
    """Prepare Development Allowance claims before saving.

    ERPNext requires payable_account on Expense Claim. For Development Allowance
    claims the actual reimbursement is done via Purchase Order or Additional
    Salary, so we auto-fill the company's default payable account to satisfy the
    validation without forcing the user to select one.
    """
    _enforce_own_claim(doc)

    if not _has_development_allowance_rows(doc):
        return

    if not doc.payable_account or doc.payable_account == 'N/A':
        company = doc.company or frappe.defaults.get_user_default("Company")
        if company:
            payable_account = frappe.get_cached_value(
                "Company", company, "default_payable_account"
            )
            if payable_account:
                doc.payable_account = payable_account

    _require_hr_remarks_on_decision(doc)
    _sync_approval_status(doc)


def _require_hr_remarks_on_decision(doc):
    """The approver must explain an approval or rejection.

    The form asks for the remarks in a dialog when Approve/Reject is clicked;
    this enforces it for every other path (API, bulk actions) as well. The
    applicant is never asked for remarks.
    """
    before = doc.get_doc_before_save()
    if not before or before.workflow_state != "Submitted":
        return
    if doc.workflow_state in ("Approved", "Rejected") and not (doc.custom_hr_remarks or "").strip():
        frappe.throw(_("HR Remarks are required to approve or reject a claim."))


def _sync_approval_status(doc):
    """Keep HRMS's internal approval_status in step with the workflow state.

    HRMS ExpenseClaim.on_submit throws "Approval Status must be 'Approved' or
    'Rejected'" while approval_status is still its default "Draft". The field is
    hidden from users, so it is derived from workflow_state here. The real
    approve/reject decision lives in workflow_state.
    """
    previous = doc.approval_status
    if doc.workflow_state == "Rejected":
        doc.approval_status = "Rejected"
    elif doc.workflow_state and doc.workflow_state != "Draft":
        doc.approval_status = "Approved"

    if doc.approval_status != previous and doc.docstatus != 2:
        # HRMS computed these before our hook ran, using the old value:
        # rejected claims get a zero sanctioned amount and the Rejected status.
        doc.calculate_total_amount()
        doc.set_status()


def before_submit_expense_claim(doc, method=None):
    """Enforce mandatory attachment and sub-type for Development Allowance rows."""
    if not _has_development_allowance_rows(doc):
        return

    _sync_approval_status(doc)
    # Safety net when no workflow state is set: never leave "Draft" at submit.
    if doc.approval_status == "Draft":
        doc.approval_status = "Approved"

    if not frappe.db.exists(
        "File",
        {
            "attached_to_doctype": "Expense Claim",
            "attached_to_name": doc.name,
        },
    ):
        frappe.throw(_("Please attach supporting documents before submitting."))

    for row in (doc.expenses or []):
        if row.expense_type == DEVELOPMENT_ALLOWANCE_COMPONENT and not row.custom_expense_sub_type:
            frappe.throw(
                _("Please select an Expense Sub-Type for row {0} (Development Allowance).").format(row.idx)
            )


def on_expense_claim_update(doc, method=None):
    """Handle Expense Claim workflow state changes for Development Allowance claims."""
    if not _has_development_allowance_rows(doc):
        return

    if not doc.workflow_state:
        return

    before = doc.get_doc_before_save()
    previous_workflow_state = before.workflow_state if before else None

    if doc.workflow_state == previous_workflow_state:
        return
    # Email notifications are sent by on_expense_claim_workflow_change below.
    # Reimbursement document creation (Purchase Order / Additional
    # Salary) is a manual HR action via the UI, not automatic on approval, so
    # handle_approved_claim is intentionally not called here.

    if doc.workflow_state == "Approved":
        create_workflow_comment(doc, "Approved")
    elif doc.workflow_state == "Rejected":
        handle_rejected_claim(doc)


def handle_approved_claim(doc):
    """Create Purchase Order or Additional Salary based on expense sub-type."""
    if _is_any_row_taxable(doc):
        create_additional_salary(doc)
    else:
        create_purchase_order(doc)


def handle_rejected_claim(doc):
    """Record the rejection (with HR remarks) in the claim's activity log.

    The email to the employee is sent by on_expense_claim_workflow_change.
    """
    create_workflow_comment(doc, "Rejected")


def create_workflow_comment(doc, status):
    """Create a workflow comment/activity log entry for the claim."""
    comment_content = f"Workflow State: {status}"

    if doc.custom_hr_remarks:
        comment_content += f"\n\nHR Remarks: {doc.custom_hr_remarks}"

    try:
        comment = frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Workflow",
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "content": comment_content,
            "comment_email": frappe.session.user,
        })
        comment.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Failed to create workflow comment: {e}")


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


EXPENSE_APPROVER_ROLE = "Expense Claim Approver"
EMAIL_BRAND_COLOR = "#1b7a3d"


def on_expense_claim_workflow_change(doc, method=None):
    """Send workflow emails for every Expense Claim.

    - -> Submitted: notify the claim's designated approver that it needs a decision.
    - -> Approved / Rejected: tell the applicant, including the HR Remarks.

    Wired to both on_update and on_update_after_submit because the Approve and
    Reject transitions happen on an already-submitted document. Delivery
    failures are logged, never raised, so a broken mail setup cannot block the
    workflow transition itself.
    """
    before = doc.get_doc_before_save()
    previous_state = before.workflow_state if before else None
    state = doc.workflow_state

    if not state or state == previous_state:
        return

    try:
        if state == "Submitted":
            _email_approver(doc)
        elif state in ("Approved", "Rejected"):
            _email_applicant(doc, state)
    except Exception:
        frappe.log_error(
            title="Expense Claim: notification email failed",
            message=frappe.get_traceback(),
        )


def _claim_summary(doc):
    types = []
    for row in (doc.expenses or []):
        label = row.expense_type or ""
        if row.custom_expense_sub_type:
            label += f" - {row.custom_expense_sub_type}"
        if label and label not in types:
            types.append(label)
    return ", ".join(types)


def _claim_amount(doc):
    amount = doc.total_claimed_amount or doc.grand_total or 0
    return fmt_money(amount, currency=doc.get("currency"))


def _render_claim_email(
    doc, banner, banner_bg, banner_fg, greeting, intro, rows, button_label, remarks=None, accent=None
):
    """Build the branded HTML body shared by all Expense Claim emails."""
    link = get_url_to_form(doc.doctype, doc.name)

    table = ""
    if rows:
        table_rows = "".join(
            '<tr style="background:{bg}"><td width="38%" style="padding:8px;color:#6b7280">{label}</td>'
            '<td style="padding:8px">{value}</td></tr>'.format(
                bg="#f9fafb" if i % 2 == 0 else "#ffffff", label=escape_html(label), value=value
            )
            for i, (label, value) in enumerate(rows)
        )
        table = (
            '<tr><td style="padding:0 28px 8px"><table width="100%" cellpadding="0" cellspacing="0" '
            'style="border:1px solid #e5e7eb;font-size:14px">' + table_rows + "</table></td></tr>"
        )

    remarks_box = ""
    if remarks is not None:
        remarks_html = escape_html(remarks).replace("\n", "<br>")
        remarks_box = (
            '<tr><td style="padding:0 28px 8px"><div style="border-left:4px solid {accent};'
            'background:{bg};padding:12px 16px"><div style="font-size:12px;color:{fg};'
            'font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">{title}</div>'
            '<div style="font-size:14px;line-height:1.5">{body}</div></div></td></tr>'
        ).format(accent=accent, bg=banner_bg, fg=banner_fg, title=_("HR Remarks"), body=remarks_html)

    return """
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#ffffff;font-family:Segoe UI,Arial,sans-serif;color:#1f2937">
<tr><td style="background:{brand};padding:18px 28px;color:#ffffff;font-size:18px;font-weight:600">Victory Farms &middot; {heading}</td></tr>
<tr><td style="background:{banner_bg};padding:10px 28px;color:{banner_fg};font-size:13px;font-weight:600">{banner}</td></tr>
<tr><td style="padding:24px 28px 8px;font-size:15px;line-height:1.5"><p style="margin:0 0 12px">{greeting}</p><p style="margin:0 0 16px">{intro}</p></td></tr>
{table}
{remarks_box}
<tr><td align="center" style="padding:24px 28px"><a href="{link}" style="background:{brand};color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:600;font-size:15px;display:inline-block">{button_label}</a></td></tr>
<tr><td style="padding:0 28px 24px;font-size:13px;color:#6b7280;line-height:1.5">{fallback}: {link}</td></tr>
<tr><td style="background:#f3f4f6;padding:12px 28px;font-size:12px;color:#9ca3af">{footer}</td></tr>
</table>
""".format(
        brand=EMAIL_BRAND_COLOR,
        heading=_("Expense Claim"),
        banner=banner,
        banner_bg=banner_bg,
        banner_fg=banner_fg,
        greeting=greeting,
        intro=intro,
        table=table,
        remarks_box=remarks_box,
        link=link,
        button_label=button_label,
        fallback=_("Button not working? Copy this link"),
        footer=_("Automated message from Victory Farms ERP. Please do not reply."),
    )


def _email_approver(doc):
    """Tell the claim's designated approver that it is waiting for a decision.

    Goes to the claim's Expense Approver (set to Vincent by get_designated_approver),
    not to everyone holding the Expense Claim Approver role, so other role holders
    are not emailed.
    """
    applicant_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    approver = doc.get("expense_approver") or get_designated_approver()
    if not approver or approver == applicant_user or not frappe.db.get_value("User", approver, "enabled"):
        frappe.log_error(
            title="Expense Claim: no approver to notify",
            message=f"{doc.name} was submitted but no enabled approver (other than the applicant) was found.",
        )
        return
    recipients = [approver]
    approver_name = frappe.db.get_value("User", approver, "first_name") or _("Approver")

    employee_name = escape_html(doc.employee_name or doc.employee)
    message = _render_claim_email(
        doc,
        banner="&#9679; " + _("Pending your review"),
        banner_bg="#fff3d6",
        banner_fg="#8a5a00",
        greeting=_("Dear {0},").format(escape_html(approver_name)),
        intro=_("{0} has submitted an expense claim that needs your decision.").format(
            "<b>{0}</b>".format(employee_name)
        ),
        rows=[
            (_("Claim number"), "<b>{0}</b>".format(doc.name)),
            (_("Employee"), "{0} ({1})".format(employee_name, doc.employee)),
            (_("Claim type"), escape_html(_claim_summary(doc)) or "-"),
            (_("Total claimed"), "<b>{0}</b>".format(_claim_amount(doc))),
            (_("Date submitted"), formatdate(doc.posting_date or today())),
        ],
        button_label=_("Review & Decide"),
    )
    note = (
        '<p style="max-width:600px;margin:12px auto;font-size:13px;color:#6b7280;'
        'font-family:Segoe UI,Arial,sans-serif">'
        + _("You will be asked for HR Remarks when you approve or reject. The applicant will see them.")
        + "</p>"
    )

    frappe.sendmail(
        recipients=recipients,
        subject=_("Action required: Expense Claim {0} from {1} ({2})").format(
            doc.name, doc.employee_name or doc.employee, _claim_amount(doc)
        ),
        message=message + note,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
    )


def _email_applicant(doc, state):
    """Tell the applicant the decision, with the HR Remarks and a link to the claim."""
    employee = frappe.db.get_value(
        "Employee", doc.employee, ["prefered_email", "user_id", "company_email"], as_dict=True
    ) or {}
    recipient = employee.get("prefered_email") or employee.get("user_id") or employee.get("company_email")
    if not recipient:
        frappe.log_error(
            title="Expense Claim: applicant has no email address",
            message=f"{doc.name}: Employee {doc.employee} has no preferred, user or company email; decision email not sent.",
        )
        return

    approved = state == "Approved"
    decided_by = frappe.get_cached_value("User", frappe.session.user, "full_name") or frappe.session.user
    verb = _("approved") if approved else _("rejected")
    colour = "#166534" if approved else "#991b1b"
    remarks = (doc.custom_hr_remarks or "").strip() or _("No remarks were provided.")

    message = _render_claim_email(
        doc,
        banner=("&#10003; " + _("Approved")) if approved else ("&#10007; " + _("Rejected")),
        banner_bg="#dcfce7" if approved else "#fee2e2",
        banner_fg=colour,
        greeting=_("Dear {0},").format(escape_html(doc.employee_name or doc.employee)),
        intro=_("Your expense claim {0} for {1} has been {2} by {3}.").format(
            "<b>{0}</b>".format(doc.name),
            "<b>{0}</b>".format(_claim_amount(doc)),
            '<b style="color:{0}">{1}</b>'.format(colour, verb),
            escape_html(decided_by),
        ),
        rows=[],
        button_label=_("View Claim"),
        remarks=remarks,
        accent="#1b7a3d" if approved else "#dc2626",
    )

    frappe.sendmail(
        recipients=[recipient],
        subject=_("Your Expense Claim {0} has been {1}").format(doc.name, verb),
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
    """Return the designated Expense Claim approver.

    The approver is the enabled User with the Expense Claim Approver role.
    If multiple users have the role, prefer the one matching the
    configured email (Vincent Njuguna). Falls back to the first
    Expense Claim Approver found.
    """
    DESIGNATED_EMAIL = "vincentn@victoryfarmskenya.com"

    # Try the designated user first
    user = frappe.db.get_value(
        "User",
        {"email": DESIGNATED_EMAIL, "enabled": 1, "name": ["in", frappe.get_all("Has Role", filters={"role": EXPENSE_APPROVER_ROLE}, pluck="parent")]},
        "name",
    )
    if user:
        return user

    # Fallback: first enabled Expense Claim Approver
    user = frappe.db.sql(
        """
        SELECT u.name
        FROM `tabUser` u
        INNER JOIN `tabHas Role` r ON r.parent = u.name
        WHERE r.role = %s
            AND u.enabled = 1
        ORDER BY u.creation ASC
        LIMIT 1
        """,
        (EXPENSE_APPROVER_ROLE,),
        as_dict=True,
    )
    return user[0].name if user else None
