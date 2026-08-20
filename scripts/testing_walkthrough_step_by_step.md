# Employee Onboarding Form — Testing Walkthrough (Click-by-Click)

## Before You Start

1. Log into **pre-production** ERPNext.
2. Go to **Awesome Bar > Employee** (or HR > Employee).
3. Click **+ Add Employee** (top right).
4. You are on a blank **New Employee** form.

---

## Basic Fields to Always Fill First

For every test, fill these fields so the test doesn't fail for unrelated reasons:

- **Employee Name**: `Test Employee 001`
- **Date of Joining**: `01-06-2026`
- **Department**: pick any (e.g., `Sales`)
- **Designation**: pick any (e.g., `Manager`)
- **Gender**: `Male` or `Female`
- **Date of Birth**: `01-01-1990`
- **Employment Type**: `Full-time`

---

## Test 1: Branch Empty → Save Allowed

1. On the New Employee form, make sure **Branch** is **blank/empty**.
2. Fill the Basic Fields above.
3. Also fill:
   - **Location**: pick any
   - **Contract Start Date**: any date
   - **Appraisal Template**: pick any
   - **Residential Status**: `Non-Resident` *(so Tax ID / SHIF are not required)*
   - **Salary Currency**: `KES`
4. Click **Save** (top right).

**Expected:** Green checkmark. Employee saves. No error about Branch.

**If it fails:** Red error says "Branch is mandatory" → Go back to Customize Form > Employee > Branch row → uncheck Mandatory → Save → Reload → retest.

---

## Test 2: Default Shift Empty → Save Allowed

1. Create another **New Employee** (or use the same one and click **+ Add Employee** again).
2. Fill Basic Fields.
3. Leave **Default Shift** blank.
4. Fill all other mandatory fields (Location, Contract Start Date, Appraisal Template, etc.).
5. Set Residential Status = `Non-Resident`, Salary Currency = `KES`.
6. Click **Save**.

**Expected:** Save succeeds. No error about Default Shift.

**If it fails:** Red error says "Default Shift is mandatory" → Go to Customize Form > Employee > Default Shift row → uncheck Mandatory → Save → Reload → retest.

---

## Test 3: Location Empty → Save Blocked

1. Create **New Employee**.
2. Fill Basic Fields.
3. Leave **Location** **blank**.
4. Fill Contract Start Date, Appraisal Template, etc.
5. Set Residential Status = `Non-Resident`, Salary Currency = `KES`.
6. Click **Save**.

**Expected:** Red error banner appears saying **"Location is mandatory"**. Save is blocked.

**If it passes (no error):** Go to Customize Form > Employee > Location row → check Mandatory → Save → Reload → retest.

---

## Test 4: Contract Start Date Empty → Save Blocked

1. Create **New Employee**.
2. Fill Basic Fields.
3. Fill Location.
4. Leave **Contract Start Date** **blank**.
5. Fill Appraisal Template.
6. Set Residential Status = `Non-Resident`, Salary Currency = `KES`.
7. Click **Save**.

**Expected:** Red error: **"Contract Start Date is mandatory"**. Save blocked.

**If it passes:** Go to Customize Form > Employee > Contract Start Date row → check Mandatory → Save → Reload → retest.

---

## Test 5: Appraisal Template Empty → Save Blocked

1. Create **New Employee**.
2. Fill Basic Fields.
3. Fill Location, Contract Start Date.
4. Leave **Appraisal Template** **blank**.
5. Set Residential Status = `Non-Resident`, Salary Currency = `KES`.
6. Click **Save**.

**Expected:** Red error: **"Appraisal Template is mandatory"**. Save blocked.

**If it passes:** Go to Customize Form > Employee > Appraisal Template row → check Mandatory → Save → Reload → retest.

---

## Test 6: Residential Status = Resident → Tax ID & SHIF No Required

1. Create **New Employee**.
2. Fill Basic Fields.
3. Fill Location, Contract Start Date, Appraisal Template.
4. Set **Residential Status** = `Resident`.
5. Leave **Tax ID** and **SHIF No** **blank**.
6. Set Salary Currency = `KES`.
7. Click **Save**.

**Expected:** Red errors: **"Tax ID is mandatory"** and **"SHIF No is mandatory"**. Save blocked.

**If it passes:** Go to Customize Form > Employee > Tax ID row → set Mandatory Depends On to `eval:doc.residential_status == 'Resident'` → Same for SHIF No → Save → Reload → retest.

---

## Test 7: Residential Status = Non-Resident → Tax ID & SHIF No NOT Required

1. Create **New Employee**.
2. Fill Basic Fields.
3. Fill Location, Contract Start Date, Appraisal Template.
4. Set **Residential Status** = `Non-Resident`.
5. Leave **Tax ID** and **SHIF No** **blank**.
6. Set Salary Currency = `KES`.
7. Click **Save**.

**Expected:** Save succeeds. No error about Tax ID or SHIF No.

**If it fails:** Red error about Tax ID or SHIF No → Check that Mandatory Depends On is correct (not unconditional Mandatory).

---

## Test 8: Salary Currency = USD → SWIFT Code Required

1. Create **New Employee**.
2. Fill Basic Fields.
3. Fill Location, Contract Start Date, Appraisal Template.
4. Set Residential Status = `Non-Resident`.
5. Set **Salary Currency** = `USD`.
6. Leave **SWIFT Code** **blank**.
7. Click **Save**.

**Expected:** Red error: **"SWIFT Code is mandatory"**. Save blocked.

**If it passes:** Go to Customize Form > Employee > SWIFT Code row → set Mandatory Depends On to `eval:doc.salary_currency == 'USD'` → Save → Reload → retest.

---

## Test 9: Salary Currency = KES → SWIFT Code NOT Required

1. Create **New Employee**.
2. Fill Basic Fields.
3. Fill Location, Contract Start Date, Appraisal Template.
4. Set Residential Status = `Non-Resident`.
5. Set **Salary Currency** = `KES`.
6. Leave **SWIFT Code** **blank**.
7. Click **Save**.

**Expected:** Save succeeds. No error about SWIFT Code.

**If it fails:** Check that SWIFT Code does not have unconditional Mandatory checked.

---

## Test 10: Relieving Date Filled → Leave Encashed? & Resignation Letter Date Required

1. Create **New Employee**.
2. Fill Basic Fields.
3. Fill Location, Contract Start Date, Appraisal Template.
4. Set Residential Status = `Non-Resident`, Salary Currency = `KES`.
5. Set **Relieving Date** = `31-12-2026`.
6. Leave **Leave Encashed?** and **Resignation Letter Date** **blank**.
7. Click **Save**.

**Expected:** Red errors: **"Leave Encashed is mandatory"** and **"Resignation Letter Date is mandatory"**. Save blocked.

**If it passes:** Check Mandatory Depends On for those fields is set to `eval:doc.relieving_date`.

---

## Test 11: Leave Encashed = Yes → Encashment Date Required

1. Use the same form from Test 10 (Relieving Date is already set).
2. Set **Leave Encashed?** = `Yes`.
3. Leave **Encashment Date** **blank**.
4. Click **Save**.

**Expected:** Red error: **"Encashment Date is mandatory"**. Save blocked.

**If it passes:** Check Mandatory Depends On for Encashment Date is `eval:doc.relieving_date && doc.leave_encashed == 'Yes'` (or `== 1` if it's a Check field).

---

## Test 12: Reason for Leaving = Resignation → Resignation Letter Required

1. Create **New Employee**.
2. Fill Basic Fields.
3. Fill Location, Contract Start Date, Appraisal Template.
4. Set Residential Status = `Non-Resident`, Salary Currency = `KES`.
5. Set **Reason for Leaving** = `Resignation`.
6. Leave **Resignation Letter** attachment **blank**.
7. Click **Save**.

**Expected:** Red error: **"Resignation Letter is mandatory"**. Save blocked.

**If it passes:** Check Mandatory Depends On for Resignation Letter is `eval:doc.reason_for_leaving == 'Resignation'`.

---

## Test 13: NHIF Field → Not Visible on Form

1. On any New Employee form, scroll through **all tabs and sections**.
2. Look for a field labeled **NHIF**.

**Expected:** **NHIF is NOT visible anywhere**.

**If you see it:** Go to Customize Form > Employee > NHIF row → check Hidden → Save → Reload.

---

## Test 14: Department Appraisal Template Autopopulate

1. Create **New Employee**.
2. Fill Basic Fields.
3. In **Department**, select a department that you know has an Appraisal Template configured (e.g., `Sales`).
4. Look at the **Department Appraisal Template** field.

**Expected:** It automatically fills with the Appraisal Template linked to that Department.

**If it doesn't:** Check that:
- The Department record has `custom_department_appraisal_template` filled
- The Employee field has Fetch From = `department.custom_department_appraisal_template`
- Fetch If Empty is checked

---

## After Testing

1. Go to **HR > Employee** list.
2. Click the checkbox next to every test employee (e.g., "Test Employee 001", "Test Employee 002", etc.).
3. Click **Actions** (top right of list) → **Delete**.
4. Confirm deletion.

---

## Test Results Tracker

| Test | Description | Pass / Fail | Notes |
|------|-------------|-------------|-------|
| 1 | Branch empty → Save allowed | | |
| 2 | Default Shift empty → Save allowed | | |
| 3 | Location empty → Save blocked | | |
| 4 | Contract Start Date empty → Save blocked | | |
| 5 | Appraisal Template empty → Save blocked | | |
| 6 | Resident → Tax ID & SHIF required | | |
| 7 | Non-Resident → Tax ID & SHIF NOT required | | |
| 8 | USD → SWIFT Code required | | |
| 9 | KES → SWIFT Code NOT required | | |
| 10 | Relieving Date → Leave Encashed? & Resignation Letter Date required | | |
| 11 | Leave Encashed = Yes → Encashment Date required | | |
| 12 | Resignation → Resignation Letter required | | |
| 13 | NHIF not visible | | |
| 14 | Department Appraisal Template autopopulates | | |

Fill this table as you test. Share the results and I'll help fix anything that fails.
