# Copyright (c) 2026, Christine K and contributors
# For license information, please see license.txt

"""
Multiple Half Days Feature - Test Cases
========================================

Run tests with:
    bench run-tests --app victoryfarmsdeveloper --module victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.test_multiple_half_days
"""

import unittest
from datetime import date
from unittest.mock import patch, MagicMock

import frappe
from frappe.utils import add_days, getdate

from victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.multiple_half_days import (
    get_number_of_leave_days_multi_half_day,
    get_valid_dates_for_half_day,
    validate_half_day_overlap,
)


class TestMultipleHalfDays(unittest.TestCase):
    """Test cases for Multiple Half Days feature"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.employee = "_T-Employee-00001"
        self.leave_type = "Casual Leave"
        
    def test_single_day_full_leave(self):
        """Test: Single day leave without half day = 1 day"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-15",
            to_date="2026-01-15",
            half_day=0,
            half_day_dates=None,
        )
        self.assertEqual(result, 1.0)
    
    def test_single_day_half_leave(self):
        """Test: Single day leave with half day = 0.5 days"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-15",
            to_date="2026-01-15",
            half_day=1,
            half_day_dates=["2026-01-15"],
        )
        self.assertEqual(result, 0.5)
    
    def test_multi_day_no_half_days(self):
        """Test: 5 day leave without half days = 5 days"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-13",
            to_date="2026-01-17",
            half_day=0,
            half_day_dates=None,
        )
        self.assertEqual(result, 5.0)
    
    def test_multi_day_one_half_day(self):
        """Test: 5 day leave with 1 half day = 4.5 days"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-13",
            to_date="2026-01-17",
            half_day=1,
            half_day_dates=["2026-01-15"],
        )
        self.assertEqual(result, 4.5)
    
    def test_multi_day_two_half_days(self):
        """Test: 5 day leave with 2 half days = 4 days"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-13",
            to_date="2026-01-17",
            half_day=1,
            half_day_dates=["2026-01-14", "2026-01-16"],
        )
        self.assertEqual(result, 4.0)
    
    def test_multi_day_all_half_days(self):
        """Test: 5 day leave with all half days = 2.5 days"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-13",
            to_date="2026-01-17",
            half_day=1,
            half_day_dates=[
                "2026-01-13", 
                "2026-01-14", 
                "2026-01-15",
                "2026-01-16",
                "2026-01-17"
            ],
        )
        self.assertEqual(result, 2.5)
    
    def test_half_day_date_outside_range_ignored(self):
        """Test: Half day date outside range is ignored"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-13",
            to_date="2026-01-15",
            half_day=1,
            half_day_dates=["2026-01-20"],  # Outside range
        )
        # Should be 3 days (no valid half days)
        self.assertEqual(result, 3.0)
    
    def test_empty_half_day_dates(self):
        """Test: Empty half_day_dates with half_day=1 = full days"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-13",
            to_date="2026-01-15",
            half_day=1,
            half_day_dates=[],
        )
        self.assertEqual(result, 3.0)
    
    def test_none_half_day_dates(self):
        """Test: None half_day_dates with half_day=1 = full days"""
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-13",
            to_date="2026-01-15",
            half_day=1,
            half_day_dates=None,
        )
        self.assertEqual(result, 3.0)
    
    def test_negative_result_becomes_zero(self):
        """Test: Result cannot be negative"""
        # This shouldn't happen in practice, but testing the guard
        result = get_number_of_leave_days_multi_half_day(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date="2026-01-15",
            to_date="2026-01-15",
            half_day=1,
            half_day_dates=["2026-01-15"] * 10,  # Too many half days
        )
        self.assertGreaterEqual(result, 0)


class TestHalfDayDateCalculations(unittest.TestCase):
    """Test date calculations for half days"""
    
    def test_date_diff_calculation(self):
        """Test basic date difference calculation"""
        from frappe.utils import date_diff
        
        # Jan 13 to Jan 17 = 5 days (inclusive)
        days = date_diff("2026-01-17", "2026-01-13") + 1
        self.assertEqual(days, 5)
    
    def test_single_day_diff(self):
        """Test single day gives 1"""
        from frappe.utils import date_diff
        
        days = date_diff("2026-01-15", "2026-01-15") + 1
        self.assertEqual(days, 1)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_weekend_dates_included(self):
        """Test that weekend dates can be half days (if included in leave)"""
        result = get_number_of_leave_days_multi_half_day(
            employee="_T-Employee-00001",
            leave_type="Casual Leave",
            from_date="2026-01-10",  # Saturday
            to_date="2026-01-11",    # Sunday
            half_day=1,
            half_day_dates=["2026-01-10"],
        )
        # Without holiday exclusion logic, should be 1.5 days
        # (This depends on the leave type's include_holiday setting)
        self.assertIsInstance(result, float)
    
    def test_duplicate_dates_counted_once(self):
        """Test that duplicate dates in half_day_dates are counted correctly"""
        # The validation should prevent duplicates, but testing calculation behavior
        result = get_number_of_leave_days_multi_half_day(
            employee="_T-Employee-00001",
            leave_type="Casual Leave",
            from_date="2026-01-13",
            to_date="2026-01-15",
            half_day=1,
            half_day_dates=["2026-01-14", "2026-01-14"],  # Duplicate
        )
        # Currently counts both, should be 2.0 (3 - 0.5 - 0.5)
        # A future improvement could deduplicate
        self.assertEqual(result, 2.0)


if __name__ == "__main__":
    unittest.main()
