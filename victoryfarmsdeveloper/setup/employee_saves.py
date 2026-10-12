import hashlib
import inspect

import frappe
from erpnext.setup.doctype.employee import employee as employee_module
from frappe.utils import cstr, getdate
from hrms.overrides import employee_master

EXPECTED_SOURCE_SHA256 = "e1a69749d6db9dde83a2223afca05928073f5e4561774ed0053cc4fef9f45517"
APPROVER_ROLES = (("leave_approver", "Leave Approver"), ("expense_approver", "Expense Approver"))
USER_FIELDS = ("first_name", "middle_name", "last_name", "birth_date", "gender", "user_image", "role_profile_name")


def watched_sources():
	return (
		employee_module.Employee.on_update,
		employee_module.Employee.update_user,
		employee_module.Employee.reset_employee_emails_cache,
		employee_master.update_approver_role,
	)


def source_sha256():
	source = "".join(inspect.getsource(fn) for fn in watched_sources())
	return hashlib.sha256(source.encode()).hexdigest()


def source_matches():
	try:
		return source_sha256() == EXPECTED_SOURCE_SHA256
	except (OSError, TypeError):
		return False


def on_update(self):
	before = self.get_doc_before_save()
	self.update_nsm_model()
	if cstr(before.reports_to if before else "") != cstr(self.reports_to):
		clear_user_permissions_cache()
	if self.user_id:
		if user_needs_update(self):
			self.update_user()
		self.update_user_permissions()
		self.update_user_status()
	if before and before.user_id and before.user_id != self.user_id:
		frappe.clear_cache(user=before.user_id)
	reset_employee_numbers_cache(self, before)


def clear_user_permissions_cache():
	frappe.cache.delete_value("user_permissions")
	frappe.db.after_commit.add(drop_user_permissions_cache)
	frappe.db.after_rollback.add(drop_user_permissions_cache)


def drop_user_permissions_cache():
	frappe.cache.delete_value("user_permissions")


def user_needs_update(employee):
	user = frappe.db.get_value("User", employee.user_id, USER_FIELDS, as_dict=True)
	if not user:
		return True
	if not user.role_profile_name and not has_role(employee.user_id, "Employee"):
		return True
	if employee.employee_name and not (user.first_name and user.last_name):
		if any(cstr(user.get(field)) != value for field, value in names_from(employee.employee_name).items()):
			return True
	if employee.date_of_birth and (not user.birth_date or getdate(user.birth_date) != getdate(employee.date_of_birth)):
		return True
	if employee.gender and user.gender != employee.gender:
		return True
	return bool(employee.image and not user.user_image)


def names_from(employee_name):
	parts = employee_name.split(" ")
	names = {"first_name": parts[0]}
	if len(parts) >= 3:
		names["middle_name"] = parts[1]
		names["last_name"] = " ".join(parts[2:])
	elif len(parts) == 2:
		names["last_name"] = parts[1]
	return names


def has_role(user, role):
	return bool(frappe.db.exists("Has Role", {"parent": user, "parenttype": "User", "role": role}))


def reset_employee_numbers_cache(employee, before):
	before = before or {}
	if cstr(employee.get("cell_number")) != cstr(before.get("cell_number")) or employee.get(
		"user_id"
	) != before.get("user_id"):
		frappe.cache.delete_value("employees_with_number")


def update_approver_role(doc, method=None):
	for field, role in APPROVER_ROLES:
		approver = doc.get(field)
		if approver and not has_role(approver, role):
			user = frappe.get_doc("User", approver)
			user.flags.ignore_permissions = True
			user.add_roles(role)


def install():
	if source_matches():
		employee_module.Employee.on_update = on_update
		employee_master.update_approver_role = update_approver_role


def is_installed():
	return (
		employee_module.Employee.on_update is on_update
		and employee_master.update_approver_role is update_approver_role
	)


def check():
	if is_installed():
		return []
	problems = [
		"ERPNext Employee.on_update or HRMS update_approver_role changed, Employee saves clear the whole site cache again"
	]
	frappe.log_error(title="Employee save cache check failed", message="\n".join(problems))
	return problems
