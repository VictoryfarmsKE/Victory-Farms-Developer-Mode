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
            e.nssf_no,
            e.last_name,
            e.first_name,
            e.middle_name,
            CONCAT_WS(' ', e.first_name, e.middle_name) AS other_names,
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
        WHERE {conditions} AND ss.custom_grade LIKE 'M%%'
        ORDER BY ss.employee
    """

    data = frappe.db.sql(sql, filters, as_dict=True)

    columns = [
        # {"label": "Salary Slip ID", "fieldname": "salary_slip_id", "fieldtype": "Link", "options": "Salary Slip", "width": 150},
        {"label": "Payroll Number", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Surname", "fieldname": "last_name", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Other Names", "fieldname": "other_names", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "ID NO", "fieldname": "national_id", "fieldtype": "Data", "width": 100},
        {"label": "KRA PIN", "fieldname": "tax_id", "fieldtype": "Data", "width": 100},
        {"label": "NSSF NO", "fieldname": "nssf_no", "fieldtype": "Data", "width": 100},
        {"label": "Gross Pay", "fieldname": "gross_pay", "fieldtype": "Currency", "width": 120},
        {"label": "Employee NSSF T1 (Gross Pay)", "fieldname": "employee_nssf_t1", "fieldtype": "Currency", "width": 120},
        {"label": "Employee NSSF T2 (Gross Pay)", "fieldname": "employee_nssf_t2", "fieldtype": "Currency", "width": 120},
        {"label": "Voluntary NSSF", "fieldname": "voluntary_nssf", "fieldtype": "Currency", "width": 120},
        {"label": "Employer NSSF T2 (Gross Pay)", "fieldname": "employer_nssf_t2", "fieldtype": "Currency", "width": 120},
        {"label": "Employer NSSF T1 (Gross Pay)", "fieldname": "employer_nssf_t1", "fieldtype": "Currency", "width": 120},
    ]

    return columns, data
