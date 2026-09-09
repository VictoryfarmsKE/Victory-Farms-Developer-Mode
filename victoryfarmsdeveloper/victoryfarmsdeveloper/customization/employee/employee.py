import frappe
from frappe import _


def validate_mandatory_fields(doc, method):
    """
    Employee mandatory field validation per Victory Farms HR spec.
    Single source of truth for server-side Employee validation.
    """

    errors = []

    # Sync custom_reasons to reason_for_leaving first so downstream validation sees it
    if doc.meta.has_field("custom_reasons") and doc.meta.has_field("reason_for_leaving"):
        if doc.custom_reasons:
            doc.reason_for_leaving = doc.custom_reasons

    # Auto-populate Attendance Device ID before validating it
    auto_populate_fields(doc)

    # --- Always-mandatory Employee fields ---
    _require(doc, "gender", _("Gender"), errors)
    _require(doc, "date_of_birth", _("Date of Birth"), errors)
    _require(doc, "date_of_joining", _("Date of Joining"), errors)
    _require(doc, "status", _("Status"), errors)
    _require(doc, "department", _("Department"), errors)
    _require(doc, "employment_type", _("Employment Type"), errors)
    _require(doc, "designation", _("Designation"), errors)
    _require(doc, "custom_job_title", _("Job Title"), errors)
    _require(doc, "reports_to", _("Reports to"), errors)
    _require(doc, "grade", _("Grade"), errors)
    _require(doc, "custom_location", _("Location"), errors)
    _require(doc, "custom_terms_of_service", _("Terms of Service"), errors)
    _require(doc, "contract_start_date", _("Contract Start Date"), errors)
    _require(doc, "cell_number", _("Mobile"), errors)
    _require(doc, "personal_email", _("Personal Email"), errors)
    _require(doc, "person_to_be_contacted", _("Emergency Contact Name"), errors)
    _require(doc, "emergency_phone_number", _("Emergency Phone"), errors)
    _require(doc, "relation", _("Relation"), errors)
    _require(doc, "attendance_device_id", _("Attendance Device ID"), errors)
    _require(doc, "holiday_list", _("Holiday List"), errors)
    _require(doc, "leave_approver", _("Leave Approver"), errors)

    # --- Payroll / Bank / Statutory (always mandatory) ---
    _require(doc, "ctc", _("Basic Salary"), errors)
    _require(doc, "salary_currency", _("Salary Currency"), errors)
    _require(doc, "salary_mode", _("Salary Mode"), errors)
    _require(doc, "custom_appraisal_template", _("Appraisal Template"), errors)
    _require(doc, "bonus_potential", _("Bonus Potential"), errors)
    _require(doc, "bank_ac_no", _("Bank A/C No."), errors)
    _require(doc, "custom_validation_id", _("Validation ID"), errors)
    _require(doc, "national_id", _("National ID"), errors)
    _require(doc, "nssf_no", _("NSSF No"), errors)
    _require(doc, "shif_no", _("SHIF No"), errors)
    _require(doc, "tax_id", _("Tax ID"), errors)
    _require(doc, "residential_status", _("Residential Status"), errors)
    _require(doc, "type_of_employee", _("Type Of Employee"), errors)
    _require(doc, "type_of_housing", _("Type Of Housing"), errors)

    # --- Bank details (mandatory unless USD + International transfer) ---
    is_usd = getattr(doc, "salary_currency", None) == "USD"
    is_intl = getattr(doc, "custom_transfer_type", None) == "International"
    bank_not_required = is_usd and is_intl

    if not bank_not_required:
        _require(doc, "bank_name", _("Bank Name"), errors)
        _require(doc, "custom_bank_code", _("Bank Code"), errors)
        _require(doc, "bank_branch_name", _("Bank Branch Name"), errors)
        _require(doc, "custom_branch_code", _("Branch Code"), errors)

    # --- Conditional: USD currency ---
    if is_usd:
        if doc.meta.has_field("custom_account_name") and not doc.custom_account_name:
            errors.append(_("Account Name is mandatory when Salary Currency is USD."))

    # --- Conditional: Resident-only statutory fields ---
    res_status = getattr(doc, "residential_status", None)
    is_resident = res_status and res_status.lower().startswith("resident")
    if is_resident:
        if doc.meta.has_field("shif_no") and not doc.shif_no:
            errors.append(_("SHIF No is mandatory for Resident employees."))
        if doc.meta.has_field("tax_id") and not doc.tax_id:
            errors.append(_("Tax ID is mandatory for Resident employees."))

    # --- Conditional: Status = Left requires Relieving Date ---
    if getattr(doc, "status", None) == "Left":
        _require(doc, "relieving_date", _("Relieving Date"), errors)

    # --- Offboarding (when Relieving Date is set) ---
    has_relieving = bool(getattr(doc, "relieving_date", None))
    if has_relieving:
        _require(doc, "reason_for_leaving", _("Reason for Leaving"), errors)
        _require(doc, "leave_encashed", _("Leave Encashed?"), errors)

        is_encashed = getattr(doc, "leave_encashed", None) in ("Yes", 1, True)
        if is_encashed:
            _require(doc, "encashment_date", _("Encashment Date"), errors)

    # --- Resignation Letter Date (only when reason is Resignation) ---
    reason_for_leaving = getattr(doc, "reason_for_leaving", None)
    if reason_for_leaving and reason_for_leaving.lower() == "resignation":
        _require(doc, "resignation_letter_date", _("Resignation Letter Date"), errors)

    # Throw all collected errors at once
    if errors:
        frappe.throw("<br>".join(errors), title=_("Missing Required Fields"))


def auto_populate_fields(doc):
    """Auto-populate Attendance Device ID from Employee Number or Name."""
    if not doc.meta.has_field("attendance_device_id"):
        return

    if doc.attendance_device_id:
        return

    emp_num = getattr(doc, "employee_number", None) or getattr(doc, "name", None)
    if emp_num and not str(emp_num).startswith("new-employee"):
        doc.attendance_device_id = emp_num


def _require(doc, fieldname, label, errors):
    """Append error if field is empty. Skips silently if field does not exist."""
    if not doc.meta.has_field(fieldname):
        return

    value = getattr(doc, fieldname, None)
    if value is None or value == "":
        errors.append(_("{0} is mandatory.").format(label))
