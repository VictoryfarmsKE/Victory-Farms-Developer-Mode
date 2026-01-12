# Multiple Half Days Feature

## Overview

This feature extends the standard HRMS Leave Application to support selecting **multiple half days** in a single leave application, instead of just one.

## Problem Statement

In the standard HRMS implementation:
- Only **ONE** date can be marked as a half day per leave application
- The `half_day_date` field is a single Date field
- This forces employees to create multiple leave applications when they need several half days

## Solution

This proof-of-concept adds:
1. A new child table DocType: **Leave Application Half Day**
2. A custom field `half_day_dates` (Table) on Leave Application
3. Custom JavaScript for selecting multiple dates
4. Override functions for leave day calculations

## Installation

### Step 1: Migrate the Database

```bash
cd ~/frappe-bench
bench migrate
```

### Step 2: Run Setup Script

```bash
bench execute victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.setup.setup_multiple_half_days
```

### Step 3: Build Assets

```bash
bench build --app victoryfarmsdeveloper
```

### Step 4: Restart & Clear Cache

```bash
bench restart
bench clear-cache
```

## Usage

1. Open a **Leave Application**
2. Select Employee, Leave Type, From Date, and To Date
3. Check the **Half Day** checkbox
4. For multi-day leaves, a dialog will appear to select which dates are half days
5. Select one or more dates
6. The **Total Leave Days** will automatically recalculate

### Example Calculations

| Leave Period | Half Days Selected | Calculation | Total |
|--------------|-------------------|-------------|-------|
| Jan 1-5 (5 days) | None | 5 | 5.0 |
| Jan 1-5 (5 days) | Jan 3 | 5 - 0.5 | 4.5 |
| Jan 1-5 (5 days) | Jan 2, Jan 4 | 5 - 1.0 | 4.0 |
| Jan 1-5 (5 days) | All 5 days | 5 - 2.5 | 2.5 |

## Technical Details

### Files Created

```
victoryfarmsdeveloper/
├── victoryfarmsdeveloper/
│   ├── doctype/
│   │   └── leave_application_half_day/    # New child DocType
│   │       ├── __init__.py
│   │       ├── leave_application_half_day.json
│   │       └── leave_application_half_day.py
│   └── customization/
│       └── leave_application/
│           ├── __init__.py
│           ├── multiple_half_days.py      # Core logic
│           ├── setup.py                    # Setup script
│           └── test_multiple_half_days.py  # Test cases
├── public/
│   └── js/
│       └── leave_application_multi_half_day.js  # UI logic
└── hooks.py                                # Updated with new JS file
```

### API Functions

#### `get_number_of_leave_days_with_multi_half_days`

Whitelisted function to calculate leave days from the client.

```python
frappe.call({
    method: "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.multiple_half_days.get_number_of_leave_days_with_multi_half_days",
    args: {
        employee: "EMP-001",
        leave_type: "Casual Leave",
        from_date: "2026-01-01",
        to_date: "2026-01-05",
        half_day: 1,
        half_day_dates: JSON.stringify(["2026-01-02", "2026-01-04"])
    }
});
```

#### `get_valid_dates_for_half_day`

Returns dates that can be selected as half days (excludes holidays).

```python
frappe.call({
    method: "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.multiple_half_days.get_valid_dates_for_half_day",
    args: {
        employee: "EMP-001",
        from_date: "2026-01-01",
        to_date: "2026-01-05",
        leave_type: "Casual Leave"
    }
});
```

## Backward Compatibility

- The original `half_day_date` field is preserved
- When the child table has entries, the first date is also stored in `half_day_date` for compatibility
- Existing leave applications with single half day continue to work

## Migration

To migrate existing single half-day entries to the new table format:

```bash
bench execute victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.setup.migrate_existing_half_days
```

## Limitations (Proof of Concept)

1. **Salary Slip Integration**: The salary slip calculation still uses the original `half_day_date` field. For full integration, `salary_slip.py` would need modification.

2. **Leave Ledger Entry**: The ledger stores total leave days but doesn't track individual half-day dates.

3. **Reports**: Leave reports may need updates to show multiple half days.

4. **Override Class**: The `MultipleHalfDayLeaveApplication` class is provided but not enabled by default. To enable:
   ```python
   # In hooks.py
   override_doctype_class = {
       "Leave Application": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.multiple_half_days.MultipleHalfDayLeaveApplication"
   }
   ```

## Future Enhancements

1. **Full Salary Slip Integration**: Modify salary calculation to check all half-day dates
2. **Attendance Records**: Create proper half-day attendance for each date
3. **Leave Balance Report**: Show breakdown of half days taken
4. **Mobile App Support**: Update mobile leave application UI
5. **Email Templates**: Include half-day details in leave notification emails

## Removal

To remove this feature:

```bash
bench execute victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.setup.remove_multiple_half_days
```

## Testing

Run tests:

```bash
bench run-tests --app victoryfarmsdeveloper --module victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.test_multiple_half_days
```

## Support

For issues or questions, contact the Victory Farms development team.
