import frappe

# The workspace shipped as "Employee", which is also a DocType name. Frappe's
# router resolves /app/<slug> to a workspace before it looks for a doctype, so
# the workspace hid the Employee list entirely. Rename rather than delete so
# anything added to the page since it was installed is kept.
OLD_NAME = "Employee"
NEW_NAME = "Employee Expenses"
MODULE = "VictoryFarmsDeveloper"


def execute():
	if frappe.db.exists("Workspace", NEW_NAME):
		return

	workspace = frappe.db.get_value(
		"Workspace", OLD_NAME, ["name", "module", "public"], as_dict=True
	)

	if not workspace:
		return

	# Only touch the one this app shipped.
	if workspace.module != MODULE:
		return

	frappe.rename_doc("Workspace", OLD_NAME, NEW_NAME, force=True)
	frappe.db.set_value("Workspace", NEW_NAME, {"label": NEW_NAME, "title": NEW_NAME})

	frappe.clear_cache()

	print(
		"VictoryFarmsDeveloper: renamed Workspace '{0}' to '{1}' (it was hiding the Employee list)".format(
			OLD_NAME, NEW_NAME
		)
	)
