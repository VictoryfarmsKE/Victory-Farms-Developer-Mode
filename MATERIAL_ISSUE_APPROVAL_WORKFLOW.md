# Material Issue Approval Workflow Implementation

## Overview
This implementation adds an approval workflow for Material Issue stock entries to prevent errors and ensure proper review before material is issued from warehouses.

## Problem Statement
Previously, the creator of a Material Issue Stock Entry could also submit it directly, which increased the risk of errors going unnoticed. This workflow introduces a mandatory approval step.

## Solution Components

### 1. Workflow Configuration (`victoryfarmsdeveloper/fixtures/workflow.json`)
A new workflow named "Material Issue Approval Workflow" has been created with the following states:

#### Workflow States:
- **Draft** (Doc Status: 0)
  - Initial state when Stock Entry is created
  - Editable by: Stock User
  - Color: Gray (Inverse)

- **Pending Approval** (Doc Status: 0)
  - After creator submits for approval
  - Editable by: Stock Manager
  - Color: Orange (Warning)

- **Approved** (Doc Status: 1)
  - Final approved and submitted state
  - Editable by: Stock Manager
  - Color: Green (Success)

- **Rejected** (Doc Status: 0)
  - If manager rejects the request
  - Editable by: Stock User (can resubmit)
  - Color: Red (Danger)

- **Cancelled** (Doc Status: 2)
  - Cancelled after approval
  - Editable by: Stock Manager
  - Color: Red (Danger)

#### Workflow Transitions:
1. **Draft → Pending Approval**: "Submit for Approval" (Stock User)
2. **Pending Approval → Approved**: "Approve" (Stock Manager)
3. **Pending Approval → Rejected**: "Reject" (Stock Manager)
4. **Rejected → Pending Approval**: "Resubmit for Approval" (Stock User)
5. **Approved → Cancelled**: "Cancel" (Stock Manager)

### 2. Server-Side Validation (`stock_entry.py`)
Added validation in the `before_submit_stock_entry` function to ensure:
- Material Issue entries can only be submitted when workflow_state = "Approved"
- Prevents bypassing the workflow through API or direct submission
- Throws error with clear message if approval is not obtained

### 3. Client-Side Enhancement (`client_script.json`)
Created "Material Issue Approval Workflow" client script that:
- Shows visual indicators for workflow status (color-coded dashboard comments)
- Prevents direct submit button for Material Issue in Draft state
- Displays alerts when Material Issue type is selected
- Performs client-side validation before submission
- Provides clear user feedback at each stage

## Installation Steps

### 1. Export Fixtures
```bash
bench --site [your-site] export-fixtures
```

### 2. Migrate the Site
```bash
bench --site [your-site] migrate
```

### 3. Verify Installation
Navigate to: **Setup → Workflow → Material Issue Approval Workflow**

Check that the workflow is active and properly configured.

## User Roles Required

### Stock User
- Can create Material Issue Stock Entries
- Can submit for approval
- Can resubmit after rejection
- Cannot approve own requests

### Stock Manager
- Can approve or reject Material Issue requests
- Can edit pending approval entries
- Can cancel approved entries
- Has override capabilities

## Usage Flow

### For Stock Users (Requesters):
1. Create a new Stock Entry
2. Select "Material Issue" as Stock Entry Type
3. Fill in all required fields (items, quantities, warehouses, etc.)
4. Save the document
5. Click "Submit for Approval" workflow action
6. Document moves to "Pending Approval" state
7. Wait for Stock Manager approval notification

### For Stock Managers (Approvers):
1. Receive notification of pending Material Issue approval
2. Open the Stock Entry document
3. Review all details:
   - Items and quantities
   - Source warehouse
   - Purpose of issue
   - Any attached documents
4. Take action:
   - **Approve**: Click "Approve" → Document is submitted (Doc Status = 1)
   - **Reject**: Click "Reject" → Document returns to "Rejected" state for correction

### After Rejection (Stock Users):
1. Open the rejected Stock Entry
2. Review rejection comments (if any)
3. Make necessary corrections
4. Click "Resubmit for Approval"
5. Document returns to "Pending Approval" state

## Email Notifications
The workflow is configured with `send_email_alert = 1`, which means:
- Stock Managers receive emails when entries are submitted for approval
- Stock Users receive emails when their requests are approved or rejected

**Note**: Ensure Email Alert rules are configured in ERPNext for these notifications.

## Benefits

1. **Error Prevention**: Two-person verification reduces errors
2. **Audit Trail**: Complete workflow history tracked
3. **Accountability**: Clear separation of duties between requesters and approvers
4. **Visibility**: Real-time status tracking for all stakeholders
5. **Compliance**: Meets internal control requirements for inventory management

## Technical Notes

### Workflow Condition
The workflow only applies when:
```javascript
doc.stock_entry_type == 'Material Issue'
```

Other Stock Entry types (Material Transfer, Material Receipt, etc.) are not affected by this workflow.

### Self-Approval Prevention
All transitions have `allow_self_approval = 0`, ensuring that:
- The same user cannot both create and approve an entry
- Proper segregation of duties is enforced

## Troubleshooting

### Issue: Workflow not appearing
**Solution**: 
1. Check that workflow is active: Setup → Workflow → Material Issue Approval Workflow
2. Verify `is_active = 1`
3. Clear cache: `bench --site [site] clear-cache`

### Issue: Submit button still visible
**Solution**:
1. Refresh the page (Ctrl + F5)
2. Check client script is enabled in fixtures
3. Verify user has Stock User role

### Issue: Cannot approve documents
**Solution**:
1. Verify user has Stock Manager role
2. Check workflow transitions allow Stock Manager to approve
3. Ensure document is in "Pending Approval" state

## Future Enhancements
Consider adding:
1. Multi-level approval for high-value issues
2. Auto-approval for small quantities
3. Department-specific approval rules
4. Integration with budget controls
5. SMS notifications for urgent approvals

## Support
For issues or questions, contact:
- Developer: Victory Farms Development Team
- Module: VictoryFarmsDeveloper
- DocType: Stock Entry

## Version History
- **v1.0** (2026-07-31): Initial implementation of Material Issue approval workflow
