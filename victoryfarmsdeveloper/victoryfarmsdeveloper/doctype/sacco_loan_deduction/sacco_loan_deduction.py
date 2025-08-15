# Copyright (c) 2025, Christine K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, get_last_day, month_diff, add_days

class SaccoLoanDeduction(Document):
	def on_submit(self):
		salary_component = frappe.db.get_value("Salary Component", {"is_for_sacco_loan_deduction": 1})
		
		payroll_date = get_last_day(self.posting_date)
		curr_month_last_date = get_last_day(today())

		total_range = month_diff(curr_month_last_date, payroll_date)

		divide_cost = total_range > 1
		total_range = min(total_range - 1, self.period_of_payment) if total_range > 1 else total_range

		for i in range(total_range):
			loan_amount = self.loan_amount
			if divide_cost:
				loan_amount /= self.period_of_payment
			if ads_name:= frappe.db.get_value("Additional Salary", {"docstatus": 0, "payroll_date": payroll_date, "salary_component": salary_component, "employee": self.employee}):
				ads_doc = frappe.get_doc("Additional Salary", ads_name)
				ads_doc.amount += loan_amount
			
			else:
				ads_doc = frappe.new_doc("Additional Salary")
				ads_doc.salary_component = salary_component
				ads_doc.employee = self.employee
				ads_doc.payroll_date = payroll_date
				ads_doc.currency = frappe.db.get_value("Employee", self.employee, "salary_currency")
				ads_doc.amount = loan_amount
				ads_doc.overwrite_salary_structure_amount = 1

			# if i == 0:
			# 	if not self.period_of_payment:
			# 		self.period_of_payment = 5 if self.loan_amount > 1000 else 1
			# 	self.db_set("remaining_payments", self.period_of_payment - 1)
			# else:
			# 	self.db_set("remaining_payments", self.remaining_payments - 1)

			opening_balance = (self.remaining_payments + 1) * loan_amount
			closing_balance = self.remaining_payments * loan_amount

			ads_doc.append("custom_store_deduction_details", {
				"store_deduction": self.name,
				"loan_amount": self.loan_amount,
				"item": self.item,
				"opening_balance": opening_balance,
				"closing_balance": closing_balance
			})
			ads_doc.save()
			payroll_date = get_last_day(add_days(payroll_date, days = 1))


def create_remaining_payments():
	from frappe.utils import today
	todays_date = today()
	if str(get_last_day(todays_date)) != str(todays_date):
		return

	ads_list = frappe.db.get_all("Sacco Loan Deduction", {"remaining_payments": [">", 0], "docstatus": 1}, pluck = "name")
	salary_component = frappe.db.get_value("Salary Component", {"is_for_sacco_loan_deduction": 1})
	for row in ads_list:
		sd_doc = frappe.get_doc("Sacco Loan Deduction", row)
		emp_data = frappe.db.get_value("Employee", sd_doc.employee, ["salary_currency", "relieving_date", "status"], as_dict = 1)
		if emp_data.status == "Inactive":
			continue
		loan_amount = sd_doc.loan_amount
		if sd_doc.period_of_payment > 1:
			loan_amount /= sd_doc.period_of_payment

		if ads_name:= frappe.db.get_value("Additional Salary", {"docstatus": 0, "payroll_date": todays_date, "salary_component": salary_component, "employee": sd_doc.employee}):
			ads_doc = frappe.get_doc("Additional Salary", ads_name)
			ads_doc.amount += loan_amount
		
		else:
			ads_doc = frappe.new_doc("Additional Salary")
			ads_doc.salary_component = salary_component
			ads_doc.employee = sd_doc.employee
			ads_doc.payroll_date = todays_date if not emp_data.relieving_date else emp_data.relieving_date
			ads_doc.currency = emp_data.salary_currency
			ads_doc.amount = loan_amount if not emp_data.relieving_date else loan_amount * sd_doc.remaining_payments
			ads_doc.overwrite_salary_structure_amount = 1
		try:
			opening_balance = sd_doc.remaining_payments * loan_amount
			if not emp_data.relieving_date:
				closing_balance = (sd_doc.remaining_payments - 1) * loan_amount
			else:
				closing_balance = 0
			ads_doc.append("custom_store_deduction_details", {
				"store_deduction": row,
				"loan_amount": sd_doc.loan_amount,
				"item": sd_doc.item,
				"opening_balance": opening_balance,
				"closing_balance": closing_balance
			})
			ads_doc.save()
			if not emp_data.relieving_date:
				sd_doc.db_set("remaining_payments", sd_doc.remaining_payments - 1)
			else:
				sd_doc.db_set("remaining_payments", 0)
		except Exception as e:
			frappe.log_error(title = f"Additional Salary Generation error for {sd_doc.employee}", message = f"{e}")
