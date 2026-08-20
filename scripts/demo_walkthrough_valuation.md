# Demo Walkthrough: Fixed Valuation & Fluctuation Report

## Before You Start
1. Log in to the ERPNext **test environment**.
2. Ensure you have a Gutted Fish-Tilapia item ready (e.g., `Large Size`) with `custom_fixed_valuation_rate` = **180.00**.
3. Ensure Processing warehouse has `custom_is_fixed_valuation_zone` = **0** and a Price Variance Account set.
4. Ensure FLC warehouse has `custom_is_fixed_valuation_zone` = **1**.

---

## Part 1: Fixed Valuation Rate (Phase 1)

### Scene 1 — Show the Setup (30 sec)
1. **Stock > Item** → open your test item.
2. Scroll to **Custom Fields** section.
3. **Point out:** `Fixed Valuation Rate` = 180.00.
4. **Stock > Warehouse** → open `Processing - VFL`.
5. **Point out:** `Is Fixed Valuation Zone` = unchecked (0), `Price Variance Account` is set.
6. Open `FLC - VFL`.
7. **Point out:** `Is Fixed Valuation Zone` = checked (1).

### Scene 2 — Transfer with Actual Cost ABOVE Fixed Rate (1 min)
1. **Stock > Stock Entry > New**.
2. **Stock Entry Type** = `Material Transfer`.
3. **From Warehouse** = `Processing - VFL`.
4. **To Warehouse** = `FLC - VFL`.
5. **Add row:**
   - Item = `Large Size`
   - Qty = 10
   - Basic Rate = **200.00** (above fixed)
6. **Save** → **Submit**.
7. **Stock Ledger Report** (or click "View Stock Ledger" on the item row):
   - **Point out:** Incoming rate = **180.00** (not 200).
8. **Accounting Ledger** (or General Ledger filtered by this Stock Entry):
   - **Point out:** A variance of **200.00** posted to the Processing variance account.
9. Click back to the Stock Entry, scroll to the item row:
   - **Point out:** `Actual Rate At Transfer` = **200.00** (audit trail).

### Scene 3 — Transfer with Actual Cost BELOW Fixed Rate (1 min)
1. **Stock > Stock Entry > New** (same setup).
2. **Basic Rate** = **160.00** (below fixed).
3. **Save** → **Submit**.
4. **Stock Ledger:** Incoming rate = **180.00**.
5. **General Ledger:** Variance of **200.00** posted again.
6. Narrate: *"The fixed rate is enforced in both directions — whether actual cost is higher or lower."*

### Scene 4 — Downstream FLC to Branch (No New Variance) (1 min)
1. **Stock > Stock Entry > New**.
2. **From Warehouse** = `FLC - VFL`.
3. **To Warehouse** = any Branch warehouse.
4. Add same item, qty = 5.
5. **Save** → **Submit**.
6. **Stock Ledger:**
   - **Point out:** Incoming rate = **180.00** (carried forward).
7. **General Ledger:**
   - **Point out:** **No new variance entry** — downstream is free.

---

## Part 2: Valuation Fluctuation Report (Phase 2)

### Scene 5 — Trigger the Report Manually (1 min)
1. **Help > System Console** (or navigate to `/app/system-console`).
2. Paste and run:

```python
result = frappe.call(
    "victoryfarmsdeveloper.notifications.valuation_fluctuation.check_valuation_fluctuations",
    analysis_date="2026-06-18",
    recipients="your-email@victoryfarmskenya.com"
)
print(result)
```

3. **Point out:** Return value shows `{'status': 'sent', 'flagged': X, 'day': '2026-06-18'}`.
4. Switch to your **email inbox**.
5. Open the email titled: *"Valuation Rate Fluctuation Alert - 2026-06-18"*.

### Scene 6 — Walk Through the Email Report (1.5 min)
1. **Key Metrics table:**
   - Total transitions, flagged count, unique items, unique warehouses.
   - Severity breakdown: CRITICAL / HIGH / MEDIUM / LOW.
2. **Flagged by Item table:**
   - Which items had the most flagged transitions.
3. **Top Warehouses table:**
   - Which warehouses are hotspots.
4. **Likely Anomalies table:**
   - The biggest swings: previous rate → new rate, % change.
5. **CSV Attachment:**
   - Download and open in Excel.
   - **Point out:** All flagged transitions in a filterable table.

### Scene 7 — Mention the Automation (15 sec)
1. Narrate: *"This runs automatically every day at 6 AM via a scheduled job in hooks.py. Finance receives this email every morning without any manual work."*

---

## Recording Tips

### Option A: Video (Recommended)
- Press **Win + Alt + R** to start recording with Xbox Game Bar (built into Windows).
- Or press **Win + G** → open Capture widget → click record.
- Record each scene in one continuous take.
- Keep narration concise: explain what you are clicking and what the result proves.

### Option B: Screenshots + Narration
- If video files are too large, take annotated screenshots (Snipping Tool).
- Use red arrows/circles to highlight the key numbers (180.00 vs 200.00, variance amount, etc.).
- Compile into a PowerPoint or Word doc with captions.

---

## Estimated Demo Duration
- **Phase 1:** ~3.5 minutes
- **Phase 2:** ~2.5 minutes
- **Total:** ~6 minutes
