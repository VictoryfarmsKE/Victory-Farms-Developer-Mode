import frappe
from frappe import _


def validate_mandatory_fields(doc, method):
    """
    Employee mandatory field validation per Victory Farms HR spec.
    Auto-populates Attendance Device ID from Employee Number to reduce manual entry errors.
    """

    auto_populate_fields(doc)

    # --- Other Employee Fields (always mandatory) ---
    _require(doc, "gender", _("Gender"))
    _require(doc, "date_of_birth", _("Date of Birth"))
    _require(doc, "date_of_joining", _("Date of Joining"))
    _require(doc, "status", _("Status"))
    _require(doc, "department", _("Department"))
    _require(doc, "employment_type", _("Employment Type"))
    _require(doc, "designation", _("Designation"))
    if doc.meta.has_field("job_title"):
        _require(doc, "job_title", _("Job Title"))
    _require(doc, "reports_to", _("Reports to"))
    _require(doc, "grade", _("Grade"))
    _require(doc, "branch", _("Location"))
    _require(doc, "terms_of_service", _("Terms of Service"))
    _require(doc, "contract_start_date", _("Contract Start Date"))
    _require(doc, "cell_number", _("Mobile"))
    _require(doc, "personal_email", _("Personal Email"))
    _require(doc, "emergency_contact_name", _("Emergency Contact Name"))
    _require(doc, "emergency_phone_number", _("Emergency Phone"))
    _require(doc, "relation", _("Relation"))
    _require(doc, "attendance_device_id", _("Attendance Device ID"))
    _require(doc, "holiday_list", _("Holiday List"))
    _require(doc, "leave_approver", _("Leave Approver"))

    # --- Payroll / Bank / Statutory (always mandatory) ---
    _require(doc, "basic_salary", _("Basic Salary"))
    _require(doc, "salary_currency", _("Salary Currency"))
    _require(doc, "salary_mode", _("Salary Mode"))
    _require(doc, "bank_name", _("Bank Name"))
    _require(doc, "appraisal_template", _("Appraisal Template"))
    _require(doc, "bonus_potential", _("Bonus Potential"))
    _require(doc, "bank_code", _("Bank Code"))
    _require(doc, "bank_branch_name", _("Bank Branch Name"))
    _require(doc, "branch_code", _("Branch Code"))
    _require(doc, "bank_ac_no", _("Bank A/C No."))
    _require(doc, "validation_id", _("Validation ID"))
    _require(doc, "national_id", _("National ID"))
    _require(doc, "nssf_no", _("NSSF No"))
    _require(doc, "custom_nssf_no", _("custom_nssf_no"))
    _require(doc, "residential_status", _("Residential Status"))
    _require(doc, "type_of_employee", _("Type Of Employee"))
    _require(doc, "custom_type_of_employee", _("Type Of Employee"))
    _require(doc, "type_of_housing", _("Type Of Housing"))
    _require(doc, "custom_type_of_housing", _("Type Of Housing"))

    # --- Conditional: USD currency ---
    if doc.salary_currency == "USD":
        if doc.meta.has_field("custom_account_name") and not doc.custom_account_name:
            frappe.throw(
                _("Account Name is mandatory when Salary Currency is USD."),
                title=_("Missing Mandatory Field")
            )
        if doc.custom_transfer_type == "International":
            if doc.meta.has_field("micr_code") and not doc.micr_code:
                frappe.throw(
                    _("SWIFT Code is mandatory for USD International transfers."),
                    title=_("Missing Mandatory Field")
                )

    # --- Conditional: Resident-only statutory fields ---
    if doc.residential_status == "Resident":
        if doc.meta.has_field("tax_id") and not doc.tax_id:
            frappe.throw(
                _("Tax PIN (Tax ID) is mandatory for employees with Residential Status = Resident."),
                title=_("Missing Mandatory Field")
            )
        if doc.meta.has_field("health_insurance_no") and not doc.health_insurance_no:
            frappe.throw(
                _("SHA Number (SHIF No) is mandatory for employees with Residential Status = Resident."),
                title=_("Missing Mandatory Field")
            )

    # --- Conditional: Status = Left requires Relieving Date ---
    if doc.status == "Left":
        _require(doc, "relieving_date", _("Relieving Date"))

    # --- Offboarding (when Relieving Date is set) ---
    if doc.relieving_date:
        _require(doc, "leave_encashed", _("Leave Encashed?"))
        _require(doc, "encashment_date", _("Encashment Date"))
        _require(doc, "reason_for_leaving", _("Reason for Leaving"))

    # --- Resignation Letter Date (only when reason is Resignation) ---
    if doc.meta.has_field("reason_for_leaving") and doc.reason_for_leaving == "Resignation":
        _require(doc, "resignation_letter_date", _("Resignation Letter Date"))


def auto_populate_fields(doc):
    """Auto-populate Attendance Device ID from Employee Number."""
    employee_number = getattr(doc, "employee_number", None)
    if employee_number and doc.meta.has_field("attendance_device_id"):
        if not doc.attendance_device_id:
            doc.attendance_device_id = employee_number


def _require(doc, fieldname, label):
    """Validates a field is populated. Skips silently if the field does not exist."""
    if not doc.meta.has_field(fieldname):
        return
    value = getattr(doc, fieldname, None)
    if not value:
        frappe.throw(
            _("{0} is mandatory.").format(label),
            title=_("Missing Mandatory Field")
        )
