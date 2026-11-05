"""
Enforces the organisation's session idle-timeout policy via System Settings.

Wired to `after_migrate` (like `purchase_receipt_field_rules` and friends)
rather than `patches.txt`, because `System Settings` is a live, editable
singleton: someone could change "Session Expiry" back via the UI, and a
one-off patch would never re-apply. Running this on every migrate keeps the
value enforced and version-controlled instead of silently drifting.

The policy is a 2-hour idle timeout with a 15-minute warning. The warning
lead time lives in `public/js/idle_session_warning.js` and must be kept in
step with the value here, since the client JS cannot read Python constants
directly.
"""

import frappe

# System Settings "Session Expiry" is stored as "HH:MM" idle timeout.
SESSION_EXPIRY = "02:00"


def enforce():
    settings = frappe.get_single("System Settings")
    if settings.session_expiry == SESSION_EXPIRY:
        return
    settings.session_expiry = SESSION_EXPIRY
    settings.save(ignore_permissions=True)
    frappe.db.commit()
