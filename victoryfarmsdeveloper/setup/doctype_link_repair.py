import frappe

RENAMED_DOCTYPES = {
	"VF Asset Maintenance Schedule": "Preventative Maintenance Schedule",
	"VF Asset Maintenance Schedule Tasks": "Preventative Maintenance Schedule Tasks",
}


def repair_renamed_links():
	for old, new in RENAMED_DOCTYPES.items():
		if frappe.db.exists("DocType", old):
			continue

		if not frappe.db.exists("DocType", new):
			continue

		rows = frappe.db.sql(
			"select name, parent from `tabDocType Link` where link_doctype = %s",
			(old,),
			as_dict=True,
		)

		if not rows:
			continue

		frappe.db.sql(
			"update `tabDocType Link` set link_doctype = %s where link_doctype = %s",
			(new, old),
		)

		for parent in {row.parent for row in rows}:
			frappe.clear_cache(doctype=parent)

		print(
			"VictoryFarmsDeveloper: repointed {0} DocType Link row(s) from {1} to {2}".format(
				len(rows), old, new
			)
		)
