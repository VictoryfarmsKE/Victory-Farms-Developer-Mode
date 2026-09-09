import frappe

MODULE = "VictoryFarmsDeveloper"
OLD_NAME = "Employee"
NEW_NAME = "Employee Expenses"


def enforce():
    old = frappe.db.get_value(
        "Workspace", OLD_NAME, ["name", "module", "content"], as_dict=True
    )

    if not old or old.module != MODULE:
        return

    new = frappe.db.get_value(
        "Workspace", NEW_NAME, ["name", "module", "content"], as_dict=True
    )

    if not new:
        frappe.rename_doc("Workspace", OLD_NAME, NEW_NAME, force=True)
        frappe.db.set_value("Workspace", NEW_NAME, {"label": NEW_NAME, "title": NEW_NAME})
        frappe.db.commit()
        frappe.clear_cache()
        print("VictoryFarmsDeveloper: renamed Workspace {0} to {1}".format(OLD_NAME, NEW_NAME))
        return

    if old.content != new.content:
        print(
            "VictoryFarmsDeveloper: Workspace {0} differs from {1}, leaving both in place".format(
                OLD_NAME, NEW_NAME
            )
        )
        return

    frappe.delete_doc("Workspace", OLD_NAME, force=True, ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache()
    print("VictoryFarmsDeveloper: removed duplicate Workspace {0}".format(OLD_NAME))
