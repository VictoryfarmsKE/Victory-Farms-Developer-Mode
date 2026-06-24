# Employee Onboarding Form — Field Changes Summary
# Paste these values into Customize Form > Employee > Details tab

## 1. REMOVE Mandatory

| Field | Mandatory | Mandatory Depends On |
|-------|-----------|---------------------|
| Branch | UNCHECK | (blank) |
| Default Shift | UNCHECK | (blank) |

## 2. MAKE Mandatory (Unconditional)

| Field | Mandatory | Mandatory Depends On |
|-------|-----------|---------------------|
| Location | CHECK | (blank) |
| Contract Start Date | CHECK | (blank) |
| Appraisal Template (or custom_department_appraisal_template) | CHECK | (blank) |

## 3. MAKE Mandatory (Conditional)

| Field | Mandatory | Mandatory Depends On |
|-------|-----------|---------------------|
| Tax ID (or tax_id) | UNCHECK | `eval:doc.residential_status == 'Resident'` |
| SHIF No (or shif_no) | UNCHECK | `eval:doc.residential_status == 'Resident'` |
| SWIFT Code (or swift_code) | UNCHECK | `eval:doc.salary_currency == 'USD'` |
| Leave Encashed (or leave_encashed) | UNCHECK | `eval:doc.relieving_date` |
| Encashment Date (or encashment_date) | UNCHECK | `eval:doc.relieving_date && doc.leave_encashed == 'Yes'` |
| Resignation Letter Date (or resignation_letter_date) | UNCHECK | `eval:doc.relieving_date` |
| Resignation Letter (attach) | UNCHECK | `eval:doc.reason_for_leaving == 'Resignation'` |

## 4. HIDE Field

| Field | Hidden |
|-------|--------|
| NHIF (or nhif) | CHECK |

## 5. Fetch From (Autopopulate)

| Field | Fetch From | Fetch If Empty |
|-------|-----------|----------------|
| Department Appraisal Template | `department.custom_department_appraisal_template` | CHECK |

## 6. New Custom Fields to Create (if they don't exist)

Use "Add Custom Field" on Customize Form > Employee.

### Account Name
- Label: Account Name
- Fieldtype: Data
- Insert After: Bonus Potential
- Mandatory: UNCHECK

### SWIFT Code
- Label: SWIFT Code
- Fieldtype: Data
- Insert After: Account Name
- Mandatory: UNCHECK
- Mandatory Depends On: `eval:doc.salary_currency == 'USD'`
- Description: Cater for International USD transfer

### Leave Encashed
- Label: Leave Encashed
- Fieldtype: Select
- Options: (paste on new lines)
  ```
  Yes
  No
  ```
- Insert After: Relieving Date
- Mandatory: UNCHECK
- Mandatory Depends On: `eval:doc.relieving_date`

### Encashment Date
- Label: Encashment Date
- Fieldtype: Date
- Insert After: Leave Encashed
- Mandatory: UNCHECK
- Mandatory Depends On: `eval:doc.relieving_date && doc.leave_encashed == 'Yes'`

### Resignation Letter Date
- Label: Resignation Letter Date
- Fieldtype: Date
- Insert After: Encashment Date
- Mandatory: UNCHECK
- Mandatory Depends On: `eval:doc.relieving_date`

### Resignation Letter (Attachment)
- Label: Resignation Letter
- Fieldtype: Attach
- Insert After: Resignation Letter Date
- Mandatory: UNCHECK
- Mandatory Depends On: `eval:doc.reason_for_leaving == 'Resignation'`

## 7. New Custom Field on Department (if it doesn't exist)

Use "Add Custom Field" on Customize Form > Department.

### Department Appraisal Template
- Label: Department Appraisal Template
- Fieldtype: Link
- Options: Appraisal Template
- Insert After: department_name (or any logical location)
- Mandatory: UNCHECK

After creating this, go to HR > Department list and manually select the correct Appraisal Template for each department.
