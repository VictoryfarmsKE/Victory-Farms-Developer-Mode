import hashlib
import inspect

import frappe
from frappe.desk.form import linked_with
from frappe.model.meta import is_single

EXPECTED_SOURCE_SHA256 = "fb5250610f5f920bda7bbac02896b291ab7a41308a2a29153b2eac816590ea07"
original_get_dynamic_linked_fields = linked_with.get_dynamic_linked_fields


def dynamic_link_fields(without_ignore_user_permissions_enabled):
	filters = [["fieldtype", "=", "Dynamic Link"]]
	if without_ignore_user_permissions_enabled:
		filters.append(["ignore_user_permissions", "!=", 1])
	links = frappe.get_all(
		"DocField",
		fields=["parent as doctype", "fieldname", "options as doctype_fieldname"],
		filters=filters,
	)
	links += frappe.get_all(
		"Custom Field",
		fields=["dt as doctype", "fieldname", "options as doctype_fieldname"],
		filters=filters,
	)
	return links


def get_dynamic_linked_fields(doctype, without_ignore_user_permissions_enabled=False):
	ret = {}
	for df in dynamic_link_fields(without_ignore_user_permissions_enabled):
		if is_single(df.doctype):
			continue
		meta = frappe.get_meta(df.doctype)
		if meta.is_virtual:
			continue
		if meta.istable:
			parenttypes = frappe.get_all(
				df.doctype,
				filters={df.doctype_fieldname: doctype},
				pluck="parenttype",
				distinct=True,
				order_by=None,
			)
			for parenttype in parenttypes:
				ret[parenttype] = {
					"child_doctype": df.doctype,
					"fieldname": [df.fieldname],
					"doctype_fieldname": df.doctype_fieldname,
				}
		elif frappe.get_all(
			df.doctype, filters={df.doctype_fieldname: doctype}, pluck="name", limit=1, order_by=None
		):
			ret[df.doctype] = {"fieldname": [df.fieldname], "doctype_fieldname": df.doctype_fieldname}
	return ret


def source_matches():
	try:
		source = inspect.getsource(original_get_dynamic_linked_fields)
	except (OSError, TypeError):
		return False
	return hashlib.sha256(source.encode()).hexdigest() == EXPECTED_SOURCE_SHA256


def install():
	if source_matches():
		linked_with.get_dynamic_linked_fields = get_dynamic_linked_fields


def is_installed():
	return linked_with.get_dynamic_linked_fields is get_dynamic_linked_fields


def check():
	install()
	if is_installed():
		return []
	problems = [
		"Frappe get_dynamic_linked_fields changed, the Links window reads every linked row again"
	]
	frappe.log_error(title="Linked doctypes scan check failed", message="\n".join(problems))
	return problems
