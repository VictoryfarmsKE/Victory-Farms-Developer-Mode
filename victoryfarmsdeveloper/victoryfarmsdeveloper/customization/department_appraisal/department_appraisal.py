import frappe
from frappe.utils import has_common
import html
import re

def has_permission(doc, ptype, user):
    if ptype != "read":
        return None

    # Allow full access to specific roles
    full_access_roles = [
        "Department Appraisal Bulk Updater",
        "System Manager",
        "Executive Manager",
        "Payroll Officer"
    ]

    user_roles = frappe.get_roles(user)
    if has_common(user_roles, full_access_roles):
        return True

    # For employees, restrict to their own department
    employee = frappe.get_value("Employee", {"user_id": user}, ["department"])
    if employee and doc.department == employee:
        return True

    return False

def get_permission_query_conditions(user):
    if not user:
        return ""

    full_access_roles = [
        "Department Appraisal Bulk Updater",
        "System Manager",
        "Executive Manager",
        "Payroll Officer"
    ]

    user_roles = frappe.get_roles(user)
    if has_common(user_roles, full_access_roles):
        return ""

    employee_department = frappe.db.get_value("Employee", {"user_id": user}, "department")
    if employee_department:
        return f"""(`tabDepartment Appraisal`.department = '{employee_department}'
                    and `tabDepartment Appraisal`.docstatus = 1 
                    and `tabDepartment Appraisal`.workflow_state = 'Approved')"""

    # If no department is found, show nothing
    return "1=0"

def clean_quill_html(html):
    # Remove outer <div class="ql-editor read-mode">...</div>
    html = re.sub(r'<div class="ql-editor read-mode">', '', html)
    html = re.sub(r'</div>\s*$', '', html)

    # Remove <p> around block-level elements like div, table
    # E.g., <p><div ...></div></p> or <p><table>...</table></p>
    block_elements = ['div', 'table', 'thead', 'tbody', 'tr', 'td', 'th']
    for tag in block_elements:
        html = re.sub(fr'<p>\s*(</?{tag}.*?)\s*</p>', r'\1', html, flags=re.DOTALL)

    # Remove empty <p><br></p> tags
    html = re.sub(r'<p><br></p>', '', html)

    # Optional: remove nested <p> inside block elements
    html = re.sub(r'<p>\s*<p>', '<p>', html)
    html = re.sub(r'</p>\s*</p>', '</p>', html)

    return html.strip()

@frappe.whitelist()
def get_rendered_scoring_references(department=None, doc_name=None):
    if not department:
        return "<p><i>Please select a department.</i></p>"

    raw_html = frappe.db.get_value(
        "Department Scoring References",
        {"department": department},
        "scoring_reference"
    )

    if not raw_html:
        return "<p><i>No goal template found for this department.</i></p>"

    try:
        # Unescape HTML entities
        unescaped = html.unescape(raw_html)
        clean_html = clean_quill_html(unescaped)
        return clean_html

    except Exception as e:
        frappe.log_error(f"Template Cleanup Error: {e}", "Scoring Template Rendering")
        return "<p><i>Error displaying goal template.</i></p>"
