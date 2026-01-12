# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

"""
Multiple Half Days Feature - Proof of Concept
==============================================

This module extends the Leave Application to support selecting multiple half days
in a single leave application.

Key Components:
1. Leave Application Half Day - Child table DocType
2. Custom Fields - Added to Leave Application
3. Override functions for leave calculation
4. Attendance creation with multiple half days
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, date_diff, add_days

from hrms.hr.doctype.leave_application.leave_application import (
    LeaveApplication,
    get_holidays,
)


class MultipleHalfDayLeaveApplication(LeaveApplication):
    """
    Extended Leave Application class that supports multiple half days.
    
    This overrides the standard LeaveApplication to:
    - Calculate leave days with multiple half day dates
    - Create attendance records for multiple half days
    - Validate half day dates are within leave period
    - Handle overlap validation for multiple half days
    """
    
    def validate(self):
        """Override validate to handle multiple half days"""
        # Call parent validation first
        super().validate()
        
        # Additional validation for multiple half days
        if self.get("half_day_dates") and cint(self.half_day):
            self.validate_multiple_half_day_dates()
            self.recalculate_total_leave_days()
    
    def validate_multiple_half_day_dates(self):
        """Validate all half day dates are within the leave period"""
        if not self.half_day_dates:
            return
            
        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        
        seen_dates = set()
        for row in self.half_day_dates:
            hd_date = getdate(row.half_day_date)
            
            # Check date is within range
            if hd_date < from_date or hd_date > to_date:
                frappe.throw(
                    _("Half Day Date {0} should be between From Date {1} and To Date {2}").format(
                        frappe.bold(row.half_day_date),
                        frappe.bold(self.from_date),
                        frappe.bold(self.to_date)
                    )
                )
            
            # Check for duplicates
            if row.half_day_date in seen_dates:
                frappe.throw(
                    _("Duplicate Half Day Date: {0}").format(frappe.bold(row.half_day_date))
                )
            seen_dates.add(row.half_day_date)
    
    def recalculate_total_leave_days(self):
        """Recalculate total leave days considering multiple half days"""
        self.total_leave_days = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=self.from_date,
            to_date=self.to_date,
            half_day=self.half_day,
            half_day_dates=[row.half_day_date for row in self.half_day_dates] if self.half_day_dates else None,
        )
    
    def get_half_day_dates_list(self):
        """Get list of half day dates from child table"""
        if not self.half_day_dates:
            # Fallback to single half_day_date for backward compatibility
            if self.half_day_date:
                return [getdate(self.half_day_date)]
            return []
        return [getdate(row.half_day_date) for row in self.half_day_dates]
    
    def create_or_update_attendance(self, attendance_name, date):
        """Override to handle multiple half day dates"""
        half_day_dates = self.get_half_day_dates_list()
        
        # Check if this date is a half day
        is_half_day = getdate(date) in half_day_dates if half_day_dates else (
            self.half_day_date and getdate(date) == getdate(self.half_day_date)
        )
        
        status = "Half Day" if is_half_day else "On Leave"
        
        if attendance_name:
            # Update existing attendance
            doc = frappe.get_doc("Attendance", attendance_name)
            half_day_status = None if status == "On Leave" else "Present"
            modify_half_day_status = 1 if doc.status == "Absent" and status == "Half Day" else 0
            doc.db_set({
                "status": status,
                "leave_type": self.leave_type,
                "leave_application": self.name,
                "half_day_status": half_day_status,
                "modify_half_day_status": modify_half_day_status,
            })
        else:
            # Create new attendance
            doc = frappe.new_doc("Attendance")
            doc.employee = self.employee
            doc.employee_name = self.employee_name
            doc.attendance_date = date
            doc.company = self.company
            doc.leave_type = self.leave_type
            doc.leave_application = self.name
            doc.status = status
            doc.half_day_status = "Present" if status == "Half Day" else None
            doc.modify_half_day_status = 1 if status == "Half Day" else 0
            doc.flags.ignore_validate = True
            doc.insert(ignore_permissions=True)
            doc.submit()


def get_number_of_leave_days_multi_half_day(
    employee: str,
    leave_type: str,
    from_date,
    to_date,
    half_day: int = None,
    half_day_dates: list = None,
    holiday_list: str = None,
) -> float:
    """
    Calculate number of leave days with support for multiple half days.
    
    Args:
        employee: Employee ID
        leave_type: Leave Type name
        from_date: Leave start date
        to_date: Leave end date
        half_day: Whether half day is enabled (1 or 0)
        half_day_dates: List of half day dates (can be multiple)
        holiday_list: Optional holiday list name
    
    Returns:
        Number of leave days as float (e.g., 3.5 for 4 days with 1 half day)
    
    Example:
        - Leave from Jan 1 to Jan 5 (5 days)
        - Half days on Jan 2 and Jan 4
        - Result: 5 - (0.5 * 2) = 4 days
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    
    # Base calculation: total days in range
    number_of_days = date_diff(to_date, from_date) + 1
    
    # Subtract 0.5 for each half day
    if cint(half_day) == 1 and half_day_dates:
        valid_half_days = 0
        for hd_date in half_day_dates:
            hd_date = getdate(hd_date)
            if from_date <= hd_date <= to_date:
                valid_half_days += 1
        
        # Each half day reduces the leave by 0.5
        number_of_days -= (0.5 * valid_half_days)
    
    # Exclude holidays if Leave Type doesn't include them
    if not frappe.db.get_value("Leave Type", leave_type, "include_holiday"):
        holidays = get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
        number_of_days = flt(number_of_days) - flt(holidays)
    
    return max(0, number_of_days)


@frappe.whitelist()
def get_number_of_leave_days_with_multi_half_days(
    employee: str,
    leave_type: str,
    from_date: str,
    to_date: str,
    half_day: int = 0,
    half_day_dates: str = None,
) -> float:
    """
    Whitelisted function to calculate leave days from client side.
    
    Args:
        employee: Employee ID
        leave_type: Leave Type name
        from_date: Leave start date (string)
        to_date: Leave end date (string)
        half_day: Whether half day is enabled (1 or 0)
        half_day_dates: JSON string of half day dates list
    
    Returns:
        Number of leave days as float
    """
    import json
    
    dates_list = None
    if half_day_dates:
        try:
            dates_list = json.loads(half_day_dates)
        except (json.JSONDecodeError, TypeError):
            dates_list = None
    
    return get_number_of_leave_days_multi_half_day(
        employee=employee,
        leave_type=leave_type,
        from_date=from_date,
        to_date=to_date,
        half_day=cint(half_day),
        half_day_dates=dates_list,
    )


@frappe.whitelist()
def get_valid_dates_for_half_day(employee: str, from_date: str, to_date: str, leave_type: str) -> list:
    """
    Get list of valid dates that can be selected as half days.
    
    This excludes:
    - Holidays (if leave type doesn't include holidays)
    - Weekly offs
    
    Args:
        employee: Employee ID
        from_date: Leave start date
        to_date: Leave end date
        leave_type: Leave Type name
    
    Returns:
        List of valid dates as strings
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    
    valid_dates = []
    include_holidays = frappe.db.get_value("Leave Type", leave_type, "include_holiday")
    
    # Get holidays if needed
    holiday_dates = set()
    if not include_holidays:
        from hrms.hr.doctype.leave_application.leave_application import get_holiday_list_for_employee
        holiday_list = get_holiday_list_for_employee(employee)
        if holiday_list:
            holidays = frappe.get_all(
                "Holiday",
                filters={
                    "parent": holiday_list,
                    "holiday_date": ["between", [from_date, to_date]]
                },
                pluck="holiday_date"
            )
            holiday_dates = set(getdate(h) for h in holidays)
    
    # Build list of valid dates
    current_date = from_date
    while current_date <= to_date:
        if current_date not in holiday_dates:
            valid_dates.append(str(current_date))
        current_date = add_days(current_date, 1)
    
    return valid_dates


def validate_half_day_overlap(employee: str, half_day_dates: list, exclude_application: str = None) -> dict:
    """
    Validate that half day dates don't overlap with existing applications.
    
    Each date can have at most 2 half-day applications (= 1 full day).
    
    Args:
        employee: Employee ID
        half_day_dates: List of half day dates to validate
        exclude_application: Leave Application name to exclude from check
    
    Returns:
        Dict with validation result and any conflicting dates
    """
    conflicts = []
    
    for hd_date in half_day_dates:
        # Count existing half-day applications on this date
        filters = {
            "employee": employee,
            "half_day": 1,
            "docstatus": ["<", 2],
            "status": ["in", ["Open", "Approved"]],
        }
        
        if exclude_application:
            filters["name"] = ["!=", exclude_application]
        
        # Check in child table
        existing_count = frappe.db.count(
            "Leave Application Half Day",
            filters={
                "half_day_date": hd_date,
                "parent": ["in", 
                    frappe.get_all("Leave Application", filters=filters, pluck="name")
                ]
            }
        )
        
        # Also check legacy single half_day_date field
        legacy_count = frappe.db.count(
            "Leave Application",
            filters={
                **filters,
                "half_day_date": hd_date
            }
        )
        
        total_existing = existing_count + legacy_count
        
        if total_existing >= 2:
            conflicts.append(hd_date)
    
    return {
        "valid": len(conflicts) == 0,
        "conflicts": conflicts,
        "message": _("The following dates already have maximum half-day applications: {0}").format(
            ", ".join(str(d) for d in conflicts)
        ) if conflicts else ""
    }
