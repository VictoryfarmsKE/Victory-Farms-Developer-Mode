import frappe
from frappe import _
from frappe.utils import getdate, get_year_start, get_year_ending


# Designation to Leave Type mapping
CD_LEVEL_DESIGNATIONS = ["Chief", "Director"]
STANDARD_ANNUAL_DESIGNATIONS = ["Manager", "Supervisor", "Laborers", "Foreman", "Pioneer"]


def create_leave_allocation_for_new_employee(doc, method):
    """
    Creates leave allocations when a new employee is created.
    
    Allocations:
    1. Everyone gets 7 days of "Sick Leave - Full Days" and "Sick Leave - Half Days"
    2. Based on designation:
       - Chief, Director → "Annual Leave C&D Level" (0 days)
       - Manager, Supervisor, Laborers, Foreman, Pioneer → "Annual Leave" (0 days)
    3. Based on gender:
       - Female → 90 days of "Maternity Leave"
       - Male → 14 days of "Paternity Leave"
    """
    try:
        # Get the current leave period dates (typically calendar year)
        today = getdate()
        from_date = doc.date_of_joining
        to_date = get_year_ending(today)
        
        employee_name = doc.name
        employee_full_name = doc.employee_name
        designation = doc.designation
        gender = doc.gender
        
        allocations_to_create = []
        
        # 1. Sick Leave allocations for everyone (7 days each)
        allocations_to_create.append({
            "leave_type": "Sick Leave - Full Days",
            "new_leaves_allocated": 7
        })
        allocations_to_create.append({
            "leave_type": "Sick Leave - Half Days",
            "new_leaves_allocated": 7
        })
        
        # 2. Annual Leave based on designation (0 days)
        if designation:
            if any(d.lower() in designation.lower() for d in CD_LEVEL_DESIGNATIONS):
                allocations_to_create.append({
                    "leave_type": "Annual Leave C&D Level",
                    "new_leaves_allocated": 0
                })
            elif any(d.lower() in designation.lower() for d in STANDARD_ANNUAL_DESIGNATIONS):
                allocations_to_create.append({
                    "leave_type": "Annual Leave",
                    "new_leaves_allocated": 0
                })
        
        if gender:
            if gender == "Female":
                allocations_to_create.append({
                    "leave_type": "Maternity Leave",
                    "new_leaves_allocated": 90
                })
            elif gender == "Male":
                allocations_to_create.append({
                    "leave_type": "Paternity Leave",
                    "new_leaves_allocated": 14
                })
        
        for allocation in allocations_to_create:
            create_leave_allocation(
                employee=employee_name,
                employee_name=employee_full_name,
                leave_type=allocation["leave_type"],
                from_date=from_date,
                to_date=to_date,
                new_leaves_allocated=allocation["new_leaves_allocated"]
            )
        
        frappe.msgprint(
            _("Leave allocations created successfully for {0}").format(employee_full_name),
            indicator="green",
            alert=True
        )
        
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Leave Allocation Creation Error for Employee: {0}").format(doc.name)
        )
        frappe.msgprint(
            _("Error creating leave allocations: {0}").format(str(e)),
            indicator="red",
            alert=True
        )


def create_leave_allocation(employee, employee_name, leave_type, from_date, to_date, new_leaves_allocated):
    """
    Creates a single leave allocation record.
    """
    if not frappe.db.exists("Leave Type", leave_type):
        frappe.log_error(
            message=_("Leave Type '{0}' does not exist").format(leave_type),
            title=_("Leave Allocation Error")
        )
        return
    
    existing_allocation = frappe.db.exists(
        "Leave Allocation",
        {
            "employee": employee,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "docstatus": ["!=", 2]
        }
    )
    
    if existing_allocation:
        frappe.log_error(
            message=_("Leave Allocation for {0} - {1} already exists for the period").format(
                employee, leave_type
            ),
            title=_("Duplicate Leave Allocation")
        )
        return
    
    try:
        leave_allocation = frappe.get_doc({
            "doctype": "Leave Allocation",
            "employee": employee,
            "employee_name": employee_name,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "new_leaves_allocated": new_leaves_allocated,
            "carry_forward": 0
        })
        
        leave_allocation.insert(ignore_permissions=True)
        leave_allocation.submit()
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Error creating Leave Allocation: {0} - {1}").format(employee, leave_type)
        )
