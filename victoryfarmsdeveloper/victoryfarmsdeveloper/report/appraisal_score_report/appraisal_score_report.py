# Copyright (c) 2024, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    
    chart = None
    if filters.get("employee"):
        chart = get_employee_chart(filters.get("employee"))

    return columns, data, None, chart

def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "ID", "fieldtype": "Link", "options": "Employee", "width": 100},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 300},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 200},
        {"label": _("Appraisal Cycle"), "fieldname": "appraisal_cycle", "fieldtype": "Link", "options": "Appraisal Cycle", "width": 200},
        {"label": _("Individual Score"), "fieldname": "individual_score", "fieldtype": "Float", "width": 200},
        {"label": _("Department Score"), "fieldname": "department_score", "fieldtype": "Float", "width": 200},
        {"label": _("Company Score"), "fieldname": "company_score", "fieldtype": "Float", "width": 200}
    ]

def get_data(filters):
    conditions = []

    if filters.get("employee"):
        conditions.append("employee.name = %(employee)s")
    if filters.get("department"):
        conditions.append("employee.department = %(department)s")
    if filters.get("company"):
        conditions.append("employee.company = %(company)s")
    if filters.get("appraisal_cycle"):
        conditions.append("appraisal_cycle.name = %(appraisal_cycle)s")
        
    conditions.append("appraisal.docstatus = 1")
    conditions.append("department_appraisal.docstatus = 1")
    conditions.append("company_appraisal.docstatus = 1")

    condition_string = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql("""
        SELECT DISTINCT
            employee.name AS ID,
            employee.employee_name AS employee_name,
            employee.department AS department,
            appraisal_cycle.name AS appraisal_cycle,
            COALESCE(appraisal.total_goal_score_percentage, 0) AS individual_score,
            COALESCE(department_appraisal.total_goal_score_percentage, 0) AS department_score,
            COALESCE(company_appraisal.score, 0) AS company_score,
            employee.bonus_potential AS bonus_potential
        FROM `tabEmployee` AS employee
        LEFT JOIN `tabAppraisal` AS appraisal ON appraisal.employee = employee.name
        LEFT JOIN `tabDepartment Appraisal` AS department_appraisal 
            ON department_appraisal.department = employee.department 
            AND department_appraisal.appraisal_cycle = appraisal.appraisal_cycle
        LEFT JOIN `tabCompany Appraisal` AS company_appraisal 
            ON company_appraisal.company = employee.company 
            AND company_appraisal.appraisal_cycle = appraisal.appraisal_cycle
        LEFT JOIN `tabAppraisal Cycle` AS appraisal_cycle ON appraisal.appraisal_cycle = appraisal_cycle.name
        WHERE {condition_string} 
        ORDER BY appraisal_cycle.start_date DESC
    """.format(condition_string=condition_string), filters, as_dict=True)

    return data

def get_employee_chart(employee):
    scores = frappe.db.sql("""
        SELECT
            appraisal.total_goal_score_percentage AS total_goal_score_percentage,
            department_appraisal.total_goal_score_percentage AS total_goal_score_percentage,
            company_appraisal.score AS score
        FROM `tabEmployee` AS employee
        LEFT JOIN `tabAppraisal` AS appraisal ON appraisal.employee = employee.name
        LEFT JOIN `tabDepartment Appraisal` AS department_appraisal ON department_appraisal.department = employee.department
        LEFT JOIN `tabCompany Appraisal` AS company_appraisal ON company_appraisal.company = employee.company
        WHERE employee.name = %s
    """, employee, as_dict=True)

    if not scores:
        return None
