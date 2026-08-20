# VictoryFarmsDeveloper Architecture

## Overview

This app is a custom Frappe/ERPNext extension for Victory Farms Kenya. It enhances HR, procurement, inventory, and performance workflows by adding:

- scheduler-based automation
- document event hooks
- desk notifications
- asynchronous background processing
- onboarding automation

## Core components

1. **hooks.py**
   - `scheduler_events` executes recurring automation tasks
   - `doc_events` binds ERP actions to custom workflows
   - `notification_config` enables desk-level alerts
   - `override_doctype_class` customizes key business documents

2. **notifications/**
   - email and scheduling logic for low stock, leave, purchase orders, appraisals, and LDCs
   - a notification config entry point for ERP desk alerts

3. **custom_scripts/server_scripts/**
   - onboarding and asset automation

4. **victoryfarmsdeveloper/victoryfarmsdeveloper/customization/**
   - custom doctype controllers for stock entry, appraisal cycles, landed cost vouchers, employee checkin, and more

## Automation flow

```text
User action or scheduler
        |
        v
ERPNext document event
        |
        v
Frappe hook (doc_events or scheduler_events)
        |
        v
Custom Python method
        |    \
        |     --> async queue (frappe.enqueue) for heavy or delayed work
        v
Business automation:
  - notifications
  - validations
  - related document creation
  - workflow state enforcement
  - reports / dashboards
```

## Key automation paths

- Employee created → leave allocations created + employee folder onboarding queued
- Leave Application update → leave balance re-check queued and notifications sent
- Purchase Order update → approval notifications and supplier PDF emails
- Stock Entry save/submit → crate validation, certificate-of-analysis creation, workflow enforcement
- Daily scheduler → low stock checks, leave balance scanning, shift update background processing, appraisal reminders
- Cron scheduler → PO reminders, old PO freezing, quarterly LDC generation, probation review notices

## Desk notification design

The new `notification_config` allows ERP users to see counts in the desk notification bell for:

- Purchase Orders pending approval
- Leave Applications needing action
- Appraisals still open
- Stock Entries requiring driver confirmation

## Async processing design

Heavy or long-running tasks are moved to the background queue using `frappe.enqueue`:

- employee folder creation
- employee checkin shift resolution
- pending appraisal notification generation
- leave balance re-checks after leave app updates

## Private testing mode

This app supports private testing without making changes official by using a local or sandbox Frappe bench environment and these best practices:

1. Run in a dedicated test site: `bench new-site victoryfarmstest` or use an existing non-production site.
2. Install the app in developer mode only for that site.
3. Use custom test data or duplicate employees, POs, leaves, and stock entries.
4. Trigger automation manually with hooks or by saving/updating documents.
5. Use the `Notification` desk bell and email queue to confirm the workflow without pushing to production.

## Testing checklist

- Create a new `Employee` and verify:
  - leave allocations are created
  - folder creation job is enqueued
- Update a `Leave Application` to `Pending Sufficient Balance` and confirm the queued leave-check job runs
- Submit a `Purchase Order` and verify the approved email workflow fires
- Create or update a `Stock Entry` and verify custom validation and workflow transitions
- Check the desk notification red dot for pending `Purchase Order`, `Leave Application`, `Appraisal`, or `Stock Entry`

## Deployment note

These improvements were added directly to the custom app code and do not require an external integration. They are safe to test in a sandboxed site before promoting to production.
