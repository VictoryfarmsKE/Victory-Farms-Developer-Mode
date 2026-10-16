# Copyright (c) 2024, Victory Farms
# Custom override for Employee Checkin to allow check-ins without geolocation
# when shift location is not configured

import frappe
from frappe import _
from hrms.hr.doctype.employee_checkin.employee_checkin import (
    EmployeeCheckin,
    CheckinRadiusExceededError,
)
from hrms.hr.utils import get_distance_between_coordinates


class CustomEmployeeCheckin(EmployeeCheckin):
    """
    Custom Employee Checkin that allows check-ins without latitude/longitude
    when the shift doesn't have a location configured.
    
    This fixes the issue where devices without GPS capability cannot create
    check-ins even when geolocation tracking is enabled but no shift location
    is configured.
    """

    def validate_distance_from_shift_location(self):
        """
        Override to only require coordinates when shift location is configured.
        
        Behavior:
        - If geolocation tracking is disabled: Allow check-in
        - If no shift location configured: Allow check-in (no coordinates required)
        - If shift location configured but radius = 0: Allow check-in (no coordinates required)
        - If shift location configured with radius > 0: Require coordinates and validate distance
        """
        if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
            return

        # First check if the shift assignment has a location configured
        assignment_locations = frappe.get_all(
            "Shift Assignment",
            filters={
                "employee": self.employee,
                "shift_type": self.shift,
                "start_date": ["<=", self.time],
                "docstatus": 1,
                "status": "Active",
            },
            or_filters=[
                ["end_date", ">=", self.time],
                ["end_date", "is", "not set"]
            ],
            fields=["name", "shift_location"],
        )

        # Build a list of allowed locations using the primary
        # Shift Location and any configured Additional Locations
        allowed_locations = []

        for assignment in assignment_locations:

            if assignment.shift_location:
                allowed_locations.append(
                    assignment.shift_location
                )

            shift_assignment = frappe.get_doc(
                "Shift Assignment",
                assignment.name
            )

            for row in (shift_assignment.custom_additional_locations or []):
                if row.location:
                    allowed_locations.append(
                        row.location
                    )

        # Remove duplicates while preserving order
        allowed_locations = list(
            dict.fromkeys(allowed_locations)
        )

        # If no location is configured, allow check-in without coordinates
        if not allowed_locations:
            return

        # Check each approved location and allow check-in
        # if the employee is within any configured radius
        for location in allowed_locations:

            checkin_radius, latitude, longitude = frappe.db.get_value(
                "Shift Location",
                location,
                ["checkin_radius", "latitude", "longitude"],
            )

            # If checkin_radius is not set or zero, skip validation
            if not checkin_radius or checkin_radius <= 0:
                return

            # Only require coordinates when shift location has a checkin radius configured
            if not (self.latitude and self.longitude):
                frappe.throw(
                    _("Latitude and longitude values are required for checking in at this shift location.")
                )

            # Latitude and longitude are provided, validate distance
            distance = get_distance_between_coordinates(
                latitude,
                longitude,
                self.latitude,
                self.longitude,
            )

            # Allow check-in if employee is within any approved location radius
            if distance <= checkin_radius:
                return

        frappe.throw(
            _("You are outside the allowed check-in radius."),
            exc=CheckinRadiusExceededError,
        )
