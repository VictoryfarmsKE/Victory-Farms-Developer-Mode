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
                "shift_location": ["is", "set"],
                "docstatus": 1,
                "status": "Active",
            },
            or_filters=[["end_date", ">=", self.time], ["end_date", "is", "not set"]],
            pluck="shift_location",
        )

        # If no shift location is configured, allow check-in without coordinates
        if not assignment_locations:
            return

        checkin_radius, latitude, longitude = frappe.db.get_value(
            "Shift Location", assignment_locations[0], ["checkin_radius", "latitude", "longitude"]
        )

        # If checkin_radius is not set or zero, skip validation
        if not checkin_radius or checkin_radius <= 0:
            return

        # Only require coordinates when shift location has a checkin radius configured
        if not (self.latitude and self.longitude):
            frappe.throw(
                _("Latitude and longitude values are required for checking in at this shift location.")
            )

        distance = get_distance_between_coordinates(
            latitude, longitude, self.latitude, self.longitude
        )
        if distance > checkin_radius:
            frappe.throw(
                _("You must be within {0} meters of your shift location to check in.").format(
                    checkin_radius
                ),
                exc=CheckinRadiusExceededError,
            )
