"""
SUVAC processing fields on Stock Entry Detail.

Wired to `after_migrate` rather than `patches.txt` for the same reason as
`purchase_receipt_field_rules`: other installed apps ship a `field_order` Property Setter
for Stock Entry Detail as a `sync_on_migrate` fixture. A `field_order` is the complete
ordered field list for a doctype, so every field missing from that snapshot stops rendering.
Upande's snapshot predates these fields and drops 20+ of them, including SUVAC's.

`sync_customizations` runs after all patches, so a patch cannot win. Only `after_migrate`
runs last, on every migrate.

`restore_hidden_fields` appends anything missing rather than replacing the list, so the
ordering other apps intend is preserved.

The SUVAC Blast transfer has no driver. `ensure_workflow_rules` adds its Warehouse Supervisor
confirmation to the `Stock Transfer` workflow and keeps it off the driver and direct submit rules.
Workflows live only in each site's database, so this runs on every migrate and only adds.
"""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "VictoryFarmsDeveloper"
DOCTYPE = "Stock Entry Detail"
LAYOUT_DOCTYPES = ("Stock Entry Detail", "Stock Entry")

CUSTOM_FIELDS = {
    DOCTYPE: [
        {
            "fieldname": "custom_line",
            "label": "Processing Line",
            "fieldtype": "Int",
            "insert_after": "fish_cage",
            "in_list_view": 1,
            "module": MODULE,
        },
        {
            "fieldname": "custom_dispatch_room",
            "label": "Dispatch Room",
            "fieldtype": "Link",
            "options": "Warehouse",
            "insert_after": "custom_line",
            "in_list_view": 1,
            "module": MODULE,
        },
    ]
}

BLAST_TRANSFER = "Fish Transfer from Processing to SUVAC Blast"
SUVAC_PROCESSING = "Fish Processing SUVAC"

STOCK_ENTRY_TYPES = [
    {"name": "Fish Transfer From FLC To Dispatch", "purpose": "Material Transfer"},
    {"name": SUVAC_PROCESSING, "purpose": "Repack"},
    {"name": BLAST_TRANSFER, "purpose": "Material Transfer", "add_to_transit": 1},
    {"name": "Fish Transfer from Cold Room to SUVAC Dispatch Room", "purpose": "Material Transfer"},
]

WORKFLOW = "Stock Transfer"
PENDING = "Pending Confirmation-Warehouse Supervisor"
CONFIRMED = "Transfer Confirmed"
IS_BLAST = 'doc.stock_entry_type == "{0}"'.format(BLAST_TRANSFER)
NOT_BLAST = 'doc.stock_entry_type != "{0}"'.format(BLAST_TRANSFER)

WORKFLOW_STATES = [
    {"state": PENDING, "doc_status": "0", "allow_edit": "Warehouse Supervisor"},
    {"state": CONFIRMED, "doc_status": "1", "allow_edit": "Warehouse Supervisor"},
    {"state": "To Amend", "doc_status": "0", "allow_edit": "Stock - VF"},
]

WORKFLOW_TRANSITIONS = [
    {"state": "Draft", "action": "Send for Confirmation", "next_state": PENDING, "allowed": "Stock - VF"},
    {"state": "Draft", "action": "Send for Confirmation", "next_state": PENDING, "allowed": "Warehouse Supervisor"},
    {"state": PENDING, "action": "Confirm", "next_state": CONFIRMED, "allowed": "Warehouse Supervisor"},
    {"state": PENDING, "action": "Return for Amendment", "next_state": "To Amend", "allowed": "Warehouse Supervisor"},
    {"state": "To Amend", "action": "Send for Confirmation", "next_state": PENDING, "allowed": "Stock - VF"},
    {"state": "To Amend", "action": "Send for Confirmation", "next_state": PENDING, "allowed": "Warehouse Supervisor"},
    {"state": CONFIRMED, "action": "Cancel", "next_state": "Cancelled", "allowed": "Warehouse Supervisor"},
]

# Existing rules the Blast transfer must not use: they would skip the supervisor or ask for a driver.
EXCLUDED_ACTIONS = ("Submit", "Send Transfer for Confirmation-Driver")

DRIVER_FIELD = "Stock Entry-driver"

# Only shown where the Driver field is, i.e. truck transfers, never on the Blast transfer.
DRIVER_FOLLOWERS = (
    "Stock Entry-custom_drivers_name",
    "Stock Entry-custom_secondary_driver",
    "Stock Entry-custom_secondary_drivers_name",
)


def enforce():
    ensure_custom_fields()
    ensure_stock_entry_types()
    ensure_driver_rule()
    ensure_workflow_rules()

    for doctype in LAYOUT_DOCTYPES:
        restore_hidden_fields(doctype)

    frappe.db.commit()

    for doctype in LAYOUT_DOCTYPES:
        frappe.clear_cache(doctype=doctype)


def ensure_custom_fields():
    fractional = frappe.db.sql(
        "select count(*) from `tabStock Entry Detail` where custom_line != floor(custom_line)"
    )[0][0] if frappe.db.has_column(DOCTYPE, "custom_line") else 0

    fields = CUSTOM_FIELDS
    if fractional:
        # Switching to Int would round these, so keep Float until they are corrected.
        fields = {DOCTYPE: [dict(f, fieldtype="Float") if f["fieldname"] == "custom_line" else f for f in CUSTOM_FIELDS[DOCTYPE]]}
        print(
            "VictoryFarmsDeveloper: Processing Line left as Float, {0} row(s) have decimals".format(fractional)
        )

    create_custom_fields(fields, ignore_validate=True)

    for field in CUSTOM_FIELDS[DOCTYPE]:
        name = frappe.db.get_value(
            "Custom Field", {"dt": DOCTYPE, "fieldname": field["fieldname"]}, "name"
        )
        if name:
            frappe.db.set_value("Custom Field", name, "module", MODULE, update_modified=False)


def ensure_stock_entry_types():
    for entry_type in STOCK_ENTRY_TYPES:
        if frappe.db.exists("Stock Entry Type", entry_type["name"]):
            continue

        doc = frappe.new_doc("Stock Entry Type")
        doc.update(entry_type)
        doc.insert(ignore_permissions=True)
        print("VictoryFarmsDeveloper: created Stock Entry Type {0}".format(entry_type["name"]))

    ensure_difference_account()


def ensure_difference_account():
    # SUVAC processing books its difference the same way as the old Fish Processing type on each site.
    field = "custom_default_difference_account"
    if not frappe.get_meta("Stock Entry Type").has_field(field):
        return

    if frappe.db.get_value("Stock Entry Type", SUVAC_PROCESSING, field):
        return

    account = frappe.db.get_value("Stock Entry Type", "Fish Processing", field)
    if not account:
        return

    frappe.db.set_value("Stock Entry Type", SUVAC_PROCESSING, field, account)
    print("VictoryFarmsDeveloper: {0} difference account set to {1}".format(SUVAC_PROCESSING, account))


def ensure_driver_rule():
    exclusion = "doc.stock_entry_type != '{0}'".format(BLAST_TRANSFER)

    field = frappe.db.get_value(
        "Custom Field", DRIVER_FIELD, ["depends_on", "mandatory_depends_on"], as_dict=True
    )
    if not field:
        return

    for key in ("depends_on", "mandatory_depends_on"):
        value = (field[key] or "").strip()
        if not value or BLAST_TRANSFER in value:
            continue
        if not value.startswith("eval:"):
            print("VictoryFarmsDeveloper: left {0} {1} as is ({2})".format(DRIVER_FIELD, key, value))
            continue

        field[key] = "{0} && {1}".format(value, exclusion)
        frappe.db.set_value("Custom Field", DRIVER_FIELD, key, field[key])
        print("VictoryFarmsDeveloper: {0} {1} now skips {2}".format(DRIVER_FIELD, key, BLAST_TRANSFER))

    driver_rule = (field.depends_on or "").strip()
    if not driver_rule:
        return

    # Empty, or the earlier Blast-only rule: safe to replace. Anything else was set on purpose.
    replaceable = ("", "eval: {0}".format(exclusion))
    for name in DRIVER_FOLLOWERS:
        if not frappe.db.exists("Custom Field", name):
            continue

        current = (frappe.db.get_value("Custom Field", name, "depends_on") or "").strip()
        if current == driver_rule:
            continue
        if current not in replaceable:
            print("VictoryFarmsDeveloper: left {0} depends_on as is ({1})".format(name, current))
            continue

        frappe.db.set_value("Custom Field", name, "depends_on", driver_rule)
        print("VictoryFarmsDeveloper: {0} now shows only with the Driver field".format(name))


def ensure_workflow_rules():
    if not frappe.db.exists("Workflow", WORKFLOW):
        return

    # Rows are written directly: saving the Workflow would also back-fill workflow_state on old entries.
    workflow = frappe.get_doc("Workflow", WORKFLOW)
    added = 0

    for state in {row["state"] for row in WORKFLOW_STATES}:
        if not frappe.db.exists("Workflow State", state):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state}).insert(
                ignore_permissions=True
            )

    for action in {row["action"] for row in WORKFLOW_TRANSITIONS}:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
                ignore_permissions=True
            )

    existing_states = {(row.state, row.allow_edit) for row in workflow.states}
    for row in WORKFLOW_STATES:
        if (row["state"], row["allow_edit"]) in existing_states:
            continue
        add_child(workflow, "states", "Workflow Document State", row)
        added += 1

    existing_transitions = {
        (row.state, row.action, row.next_state, row.allowed)
        for row in workflow.transitions
        if row.condition == IS_BLAST
    }
    for row in WORKFLOW_TRANSITIONS:
        if (row["state"], row["action"], row["next_state"], row["allowed"]) in existing_transitions:
            continue
        add_child(workflow, "transitions", "Workflow Transition", dict(row, condition=IS_BLAST))
        added += 1

    excluded = 0
    for row in workflow.transitions:
        if row.state not in ("Draft", "To Amend") or row.action not in EXCLUDED_ACTIONS:
            continue
        condition = (row.condition or "").strip()
        if BLAST_TRANSFER in condition or "outgoing_stock_entry != None" in condition:
            continue
        condition = "{0} and {1}".format(condition, NOT_BLAST) if condition else NOT_BLAST
        frappe.db.set_value("Workflow Transition", row.name, "condition", condition, update_modified=False)
        excluded += 1

    if added or excluded:
        frappe.clear_cache(doctype="Stock Entry")
        print(
            "VictoryFarmsDeveloper: {0} workflow: added {1} row(s), kept {2} rule(s) off {3}".format(
                WORKFLOW, added, excluded, BLAST_TRANSFER
            )
        )


def add_child(workflow, parentfield, doctype, values):
    idx = frappe.db.count(doctype, {"parent": workflow.name, "parentfield": parentfield}) + 1
    child = frappe.get_doc(
        dict(
            values,
            doctype=doctype,
            parent=workflow.name,
            parenttype="Workflow",
            parentfield=parentfield,
            idx=idx,
        )
    )
    child.db_insert()


def restore_hidden_fields(doctype):
    setter = "{0}-main-field_order".format(doctype)
    value = frappe.db.get_value("Property Setter", setter, "value")
    if not value:
        return

    try:
        order = json.loads(value)
    except ValueError:
        return

    if not isinstance(order, list):
        return

    cleaned = [fieldname for fieldname in order if fieldname]
    dropped = len(order) - len(cleaned)
    order = cleaned

    anchors = {}
    missing = []
    for field in frappe.get_meta(doctype).fields:
        if not field.fieldname or field.fieldname in order:
            continue
        missing.append(field.fieldname)
        anchors[field.fieldname] = frappe.db.get_value(
            "Custom Field", {"dt": doctype, "fieldname": field.fieldname}, "insert_after"
        )

    if not missing and not dropped:
        return

    pending = list(missing)
    while pending:
        placed = []
        for fieldname in pending:
            anchor = anchors.get(fieldname)
            if anchor and anchor in order:
                order.insert(order.index(anchor) + 1, fieldname)
                placed.append(fieldname)

        if not placed:
            order.extend(pending)
            break

        for fieldname in placed:
            pending.remove(fieldname)

    frappe.db.set_value(
        "Property Setter",
        setter,
        "value",
        json.dumps(order),
        update_modified=False,
    )

    if dropped:
        print(
            "VictoryFarmsDeveloper: dropped {0} empty entry(s) from the {1} layout".format(
                dropped, doctype
            )
        )

    if missing:
        print(
            "VictoryFarmsDeveloper: restored {0} hidden field(s) on {1}: {2}".format(
                len(missing), doctype, ", ".join(missing)
            )
        )
