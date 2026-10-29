"""
Enforces the organisation's session idle-timeout policy via System Settings.

Wired to `after_migrate` (like `purchase_receipt_field_rules` and friends)
rather than `patches.txt`, because `System Settings` is a live, editable
singleton: someone could change "Session Expiry" back via the UI, and a
one-off patch would never re-apply. Running this on every migrate keeps the
value enforced and version-controlled instead of silently drifting.

TEST MODE is currently active: a short 15-minute idle timeout with a 5-minute
warning, so the idle-timeout flow and warning UI (see
`public/js/idle_session_warning.js`) can be verified quickly without waiting
around for a long window to elapse.

Once verified, flip `TEST_MODE` to `False` to move to the production policy:
a 2-hour idle timeout with a 15-minute warning. The warning lead time lives
in `public/js/idle_session_warning.js` and must be switched at the same time
-- the two are intentionally kept as a single `TEST_MODE` flag in each file
rather than one shared source, since the client JS cannot read Python
constants directly.
"""

import frappe

TEST_MODE = True

# System Settings "Session Expiry" is stored as "HH:MM" idle timeout.
SESSION_EXPIRY = "00:15" if TEST_MODE else "02:00"


def enforce():
    settings = frappe.get_single("System Settings")
    if settings.session_expiry == SESSION_EXPIRY:
        return
    settings.session_expiry = SESSION_EXPIRY
    settings.save(ignore_permissions=True)
    frappe.db.commit()
