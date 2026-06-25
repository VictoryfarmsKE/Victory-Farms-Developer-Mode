"""
Seed demo data for Phase 2 (Valuation Fluctuation Report).

Run this in ERPNext System Console to create a deliberate valuation swing
so the report has something to flag.

STEPS:
1. Go to Help > System Console in ERPNext test environment.
2. Paste the entire script below.
3. Click "Execute".
4. Check the printed output for confirmation.

WARNING: Only run this on the TEST environment. It creates a Stock
Reconciliation that will alter stock valuation.
"""

import frappe
from frappe.utils import flt, now, getdate, add_days

# ---------------------------------------------------------------------------
# CONFIG -- adjust these to match your test environment
# ---------------------------------------------------------------------------
TEST_ITEM = "Large Size"          # Must be a Gutted Fish-Tilapia item
TEST_WAREHOUSE = "FLC - VFL"      # Must have stock history (at least one SLE)
ANALYSIS_DATE = "2026-06-18"      # Date the report will scan
QTY = 10
NEW_RATE = 250.00                 # Deliberately high to trigger >10% / >20 KSH
COMPANY = "Victory Farms Ltd"

# ---------------------------------------------------------------------------
# STEP 1: Verify the item exists and get its current valuation rate
# ---------------------------------------------------------------------------
item_exists = frappe.db.exists("Item", TEST_ITEM)
if not item_exists:
    frappe.throw("Item '{}' not found. Change TEST_ITEM in the script.".format(TEST_ITEM))

# Get the most recent SLE to know the current rate
last_sle = frappe.db.sql("""
    SELECT valuation_rate
    FROM `tabStock Ledger Entry`
    WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
    ORDER BY posting_date DESC, posting_time DESC, creation DESC
    LIMIT 1
""", (TEST_ITEM, TEST_WAREHOUSE), as_dict=True)

if not last_sle:
    frappe.throw(
        "No Stock Ledger history for {} in {}. "
        "Create at least one stock entry first.".format(TEST_ITEM, TEST_WAREHOUSE)
    )

prev_rate = flt(last_sle[0].valuation_rate)
print("Previous valuation rate for {} in {}: {:.2f}".format(TEST_ITEM, TEST_WAREHOUSE, prev_rate))

# ---------------------------------------------------------------------------
# STEP 2: Create a Stock Reconciliation to force a big swing
# ---------------------------------------------------------------------------
# We use Stock Reconciliation because it directly sets valuation_rate
# and creates a clear consecutive transition for the LAG() query.

sr = frappe.get_doc({
    "doctype": "Stock Reconciliation",
    "purpose": "Stock Reconciliation",
    "posting_date": ANALYSIS_DATE,
    "posting_time": "10:00:00",
    "company": COMPANY,
    "expense_account": "Stock Adjustment - VFL",  # change if your CoA differs
    "items": [{
        "item_code": TEST_ITEM,
        "warehouse": TEST_WAREHOUSE,
        "qty": QTY,
        "valuation_rate": NEW_RATE,
    }]
})

sr.save()
sr.submit()

print("Created Stock Reconciliation: {}".format(sr.name))
print("New valuation rate set to: {:.2f}".format(NEW_RATE))
print("Expected swing: {:.2f} -> {:.2f} (change: {:.2f}, pct: {:.1f}%)".format(
    prev_rate, NEW_RATE, NEW_RATE - prev_rate,
    ((NEW_RATE - prev_rate) / prev_rate * 100.0) if prev_rate else float('inf')
))

# ---------------------------------------------------------------------------
# STEP 3: Verify the SLE was created
# ---------------------------------------------------------------------------
sle_check = frappe.db.sql("""
    SELECT valuation_rate
    FROM `tabStock Ledger Entry`
    WHERE item_code = %s AND warehouse = %s
      AND posting_date = %s AND is_cancelled = 0
    ORDER BY creation DESC LIMIT 1
""", (TEST_ITEM, TEST_WAREHOUSE, ANALYSIS_DATE), as_dict=True)

if sle_check:
    print("Verified: SLE created with rate {:.2f}".format(flt(sle_check[0].valuation_rate)))
else:
    print("WARNING: No SLE found for the reconciliation date.")

# ---------------------------------------------------------------------------
# STEP 4: (Optional) Trigger the report immediately
# ---------------------------------------------------------------------------
# Uncomment the lines below if you want to trigger the report right away.
# result = frappe.call(
#     "victoryfarmsdeveloper.notifications.valuation_fluctuation.check_valuation_fluctuations",
#     analysis_date=ANALYSIS_DATE,
#     recipients="christinek@victoryfarmskenya.com"
# )
# print("Report result:", result)
