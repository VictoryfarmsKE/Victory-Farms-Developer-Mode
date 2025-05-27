# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    employee = filters.get("employee")
    company = filters.get("company")

    conditions = "ss.docstatus = 1"
    if from_date:
        conditions += " AND ss.start_date >= %(from_date)s"
    if to_date:
        conditions += " AND ss.end_date <= %(to_date)s"
    if employee:
        conditions += " AND ss.employee = %(employee)s"
    if company:
        conditions += " AND ss.company = %(company)s"

    sql = f"""
        SELECT
            ss.name AS salary_slip_id,
            ss.employee,
            ss.employee_name,
            e.national_id,
            e.tax_id,
            ss.gross_pay,
            (SELECT sd.amount FROM `tabSalary Detail` sd WHERE sd.parent = ss.name AND sd.salary_component = 'Employee NSSF T1' LIMIT 1) AS employee_nssf_t1,
            (SELECT sd.amount FROM `tabSalary Detail` sd WHERE sd.parent = ss.name AND sd.salary_component = 'Employee NSSF T2' LIMIT 1) AS employee_nssf_t2,
            (SELECT sd.amount FROM `tabSalary Detail` sd WHERE sd.parent = ss.name AND sd.salary_component = 'Voluntary NSSF' LIMIT 1) AS voluntary_nssf,
            (SELECT sd.amount FROM `tabSalary Detail` sd WHERE sd.parent = ss.name AND sd.salary_component = 'Employer NSSF T2' LIMIT 1) AS employer_nssf_t2,
            (SELECT sd.amount FROM `tabSalary Detail` sd WHERE sd.parent = ss.name AND sd.salary_component = 'Employer NSSF T1' LIMIT 1) AS employer_nssf_t1
        FROM
            `tabSalary Slip` ss
        JOIN
            `tabEmployee` e ON ss.employee = e.name
        WHERE {conditions} AND ss.custom_grade NOT LIKE 'M%%'
        ORDER BY ss.employee
    """

    data = frappe.db.sql(sql, filters, as_dict=True)

    columns = [
       	{"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Full Name", "fieldname": "employee_name", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "National ID", "fieldname": "national_id", "fieldtype": "Data", "width": 100},
        {"label": "Tax ID", "fieldname": "tax_id", "fieldtype": "Data", "width": 100},
        {"label": "Total Gross Pay", "fieldname": "gross_pay", "fieldtype": "Currency", "width": 120},
        {"label": "Employee NSSF T1 (Gross Pay)", "fieldname": "employee_nssf_t1", "fieldtype": "Currency", "width": 120},
        {"label": "Employee NSSF T2 (Gross Pay)", "fieldname": "employee_nssf_t2", "fieldtype": "Currency", "width": 120},
        {"label": "Employer NSSF T2 (Gross Pay)", "fieldname": "employer_nssf_t2", "fieldtype": "Currency", "width": 120},
        {"label": "Employer NSSF T1 (Gross Pay)", "fieldname": "employer_nssf_t1", "fieldtype": "Currency", "width": 120},
    ]

    return columns, data
