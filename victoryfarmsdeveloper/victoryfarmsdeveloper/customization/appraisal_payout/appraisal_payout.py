# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from pypika import Order
from frappe.utils import flt, add_days

class CustomAppraisalPayout(Document):

	def get_emp_list(self):
		"""
		Returns list of active employees based on selected criteria
		"""
		filters = self.make_filters()
		cond = get_filter_condition(filters)
		cond += f" and t1.custom_not_eligible_for_appraisal_payout = 0"
		if not self.employee_grade:
			grades = frappe.db.get_all("Employee Grade", {"custom_payout_frequency": self.payout_frequency}, pluck = "name")
			grade_tuple = (", ".join(["'"+ o +"'" for o in grades]))
			cond += f" and t1.grade in ({grade_tuple})"
		emp_list = get_emp_list(cond)
		emp_list = self.remove_emp(emp_list)
		return emp_list

	def remove_emp(self, emp_list):
		new_emp_list = []
		for row in emp_list:
			if row.relieving_date and row.relieving_date.__str__() < self.start_date:
				continue
			new_emp_list.append(row)
		return new_emp_list

	def make_filters(self):
		filters = frappe._dict()
		filters["company"] = self.company
		filters["branch"] = self.branch
		filters["department"] = self.department
		filters["designation"] = self.designation
		filters["grade"] = self.employee_grade

		return filters

	@frappe.whitelist()
	def fill_employee_details(self): 
		self.set("appraisal_payout_details", [])
		employees = self.get_emp_list()
		if not employees:
			error_msg = _(
				"No employees found for the mentioned criteria:<br>Company: {0}"
			).format(
				frappe.bold(self.company)
			)
			if self.branch:
				error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
			if self.department:
				error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
			if self.designation:
				error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
			if self.employee_grade:
				error_msg += "<br>" + _("Employee grade: {0}").format(frappe.bold(self.employee_grade))
			frappe.throw(error_msg, title=_("No employees found"))

		for d in employees:
			self.append("appraisal_payout_details", d)

	def get_individual_appraisal_score(self, employee):

		if date_of_joining := frappe.db.get_value("Employee", employee, "date_of_joining"):
			if self.payout_frequency == "Monthly" and add_days(self.start_date, days = 10) < date_of_joining.__str__() <= self.end_date:
				return 0

		appraisal = DocType('Appraisal')
		appraisal_cycle = DocType('Appraisal Cycle')
		individual_score = (
				frappe.qb.from_(appraisal)
				.inner_join(appraisal_cycle)
				.on(appraisal.appraisal_cycle == appraisal_cycle.name)
				.select(appraisal.total_goal_score_percentage)
				.where(
					(appraisal.employee == employee)
					& (appraisal.docstatus == 1)
					& (appraisal_cycle.start_date[self.start_date:self.end_date])
					& (appraisal_cycle.end_date[self.start_date:self.end_date]))
			).run(as_list = True)
		individual_score = [item for sublist in individual_score for item in sublist] if individual_score else individual_score
		# len_of_score = len([x for x in individual_score if x > 0])s
		individual_score = flt(sum(individual_score) / len(individual_score), 2) if individual_score else 0
		#individual_score = flt(sum(individual_score) / len_of_score, 0) if len_of_score > 0 else 0

		return individual_score

	def get_department_appraisal_score(self, department, employee=None):
		department_appraisal = DocType('Department Appraisal')
		appraisal_cycle = DocType('Appraisal Cycle')
		start_date = self.start_date

		# Fetch all department appraisal scores in the relevant period
		department_scores = (
			frappe.qb.from_(department_appraisal)
			.inner_join(appraisal_cycle)
			.on(department_appraisal.appraisal_cycle == appraisal_cycle.name)
			.select(department_appraisal.total_goal_score_percentage, appraisal_cycle.start_date, appraisal_cycle.end_date)
			.where(
				(department_appraisal.department == department)
				& (department_appraisal.docstatus == 1)
				& (appraisal_cycle.start_date[start_date:self.end_date])
				& (appraisal_cycle.end_date[start_date:self.end_date])
			)
		).run(as_list=True)

		# Only count months the employee actually worked
		if employee:
			date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
			if date_of_joining:
				date_of_joining = frappe.utils.getdate(date_of_joining)
				filtered_scores = []
				for score, cycle_start, cycle_end in department_scores:
					cycle_end_date = frappe.utils.getdate(cycle_end)
					# Include if cycle's end date is on or after joining date
					if cycle_end_date >= date_of_joining:
						filtered_scores.append(score)
				department_scores = filtered_scores
			else:
				department_scores = [score for score, _, _ in department_scores]
		else:
			department_scores = [score for score, _, _ in department_scores]

		department_score = flt(sum(department_scores) / len(department_scores), 3) if department_scores else 0

		return department_score

	def get_company_appraisal_score(self):
		company_appraisal = DocType('Company Appraisal')
		appraisal_cycle = DocType('Appraisal Cycle')
		company_score = (
				frappe.qb.from_(company_appraisal)
				.inner_join(appraisal_cycle)
				.on(company_appraisal.appraisal_cycle == appraisal_cycle.name)
				.select(company_appraisal.score)
				.where(
					(company_appraisal.company == self.company)
					& (company_appraisal.docstatus == 1)
					& (appraisal_cycle.start_date[self.start_date:self.end_date])
					& (appraisal_cycle.end_date[self.start_date:self.end_date])
				)
			).run(as_list = True)
		company_score = [item for sublist in company_score for item in sublist] if company_score else company_score
		company_score = flt(sum(company_score) / len(company_score), 2) if company_score else 0

		return company_score

	def get_matrix_percent(self, individual_score):
		"""Get percentage from matrix"""
		matrix = DocType('New Earned Bonus vs Attained Score')
		matrix_percent = (
			frappe.qb.from_(matrix)
			.select(matrix.attained_score)
			.where(
				(individual_score >= matrix.lower_limit)
				& (individual_score <= matrix.upper_limit)
			)
		).run(as_list = True)
		matrix_percent = [item for sublist in matrix_percent for item in sublist][0] if matrix_percent else 0.0

		return matrix_percent

	def get_bonus_percent(self, bonus_potential = 0, appraisal_score = 0):
		if not bonus_potential:
			return appraisal_score

		return (appraisal_score * bonus_potential) / 100
	
	def get_amount_used_for_bonus_calculation(self, employee):
		if self.payout_frequency != "Monthly":
			salary_slip = DocType('Salary Slip')
			salary_details = DocType('Salary Detail')
			sum_basic_salary = frappe.qb.functions('SUM', salary_details.amount).as_('basic_salary')
			basic_salary = (
				frappe.qb.from_(salary_slip)
				.inner_join(salary_details)
				.on(salary_details.parent == salary_slip.name)
				.select(sum_basic_salary)
				.where(
				(salary_slip.employee == employee)
				& (salary_slip.start_date[self.start_date:self.end_date])
				& (salary_slip.end_date[self.start_date:self.end_date])
				& (salary_slip.docstatus == 1)
				& (salary_details.salary_component.isin(["Basic Salary", "Basic Pay"]))
				)
			).run(as_list = True)

			basic_salary =  basic_salary[0][0] if basic_salary else 0
		else:
			basic_salary = get_base_from_most_recent_salary_structure_assignment(employee)

		return basic_salary

	@frappe.whitelist()
	def calculate_scores_and_payout(self):
		company_bonus_potential = frappe.db.get_value("Company", self.company, "custom_bonus_potential_company")
		nv_setting_doc = frappe.get_cached_doc("Navari Custom Payroll Settings")
		for entry in self.appraisal_payout_details:
			bonus_calculation_amount = self.get_amount_used_for_bonus_calculation(entry.employee)

			individual_score = self.get_individual_appraisal_score(entry.employee)
			entry.individual_score = individual_score
			entry.individual_score_value = (individual_score * 5) / 100
			matrix_percent = self.get_matrix_percent(entry.individual_score)
			individual_bonus_percent = self.get_bonus_percent(entry.bonus_potential, matrix_percent)
   

			department_score = self.get_department_appraisal_score(entry.department, entry.employee)
			entry.department_score = department_score
			entry.department_score_value = (department_score * 5) / 100
			matrix_percent = self.get_matrix_percent(entry.department_score)
			department_bonus_percent = self.get_bonus_percent(entry.bonus_potential_department, matrix_percent)

			company_score = self.get_company_appraisal_score()
			entry.company_score = company_score
			company_bonus_percent = self.get_bonus_percent(company_bonus_potential, appraisal_score=company_score)

			# total_goal_score = ((entry.individual_score_value * entry.bonus_potential) + (entry.department_score_value * entry.bonus_potential_department)) / ((entry.bonus_potential + entry.bonus_potential_department)/100)

			# Rule: Scenario 1 (primary eligibility)
			# - Require BOTH department_score_value > min_avg_score_for_bonus AND individual_score_value > min_individual_score_for_bonus
			# - Do NOT award individual bonus if bonus_potential == 0 (no individual eligibility when potential is zero)
			# - Awards department/company bonuses proportionally when amounts/percents are present
			if (
				entry.department_score_value > nv_setting_doc.min_avg_score_for_bonus
				and entry.individual_score_value > nv_setting_doc.min_individual_score_for_bonus
			):
				# award individual bonus only when there is a positive individual bonus potential
				if bonus_calculation_amount and individual_bonus_percent and entry.bonus_potential:
					entry.individual_bonus = (individual_bonus_percent / 100) * bonus_calculation_amount

				# department and company bonuses are independent of individual bonus potential here
				if bonus_calculation_amount and department_bonus_percent:
					entry.department_bonus = (department_bonus_percent / 100) * bonus_calculation_amount

				if bonus_calculation_amount and company_bonus_percent:
					entry.company_bonus = (company_bonus_percent / 100) * bonus_calculation_amount

			# Rule: Scenario 2 (department-only path)
			# - Award DEPARTMENT bonus ONLY when individual bonus_potential == 0 and department_score_value > min_avg_score_for_bonus
			# - This path does not require individual_score_value to exceed the minimum and does not award individual/company bonuses here
			elif entry.bonus_potential == 0 and entry.department_score_value > nv_setting_doc.min_avg_score_for_bonus:
			# elif entry.individual_score_value > nv_setting_doc.consider_poor_performance and entry.department_score_value > nv_setting_doc.min_avg_score_for_bonus:
				# if bonus_calculation_amount and individual_bonus_percent:
				# 	entry.individual_bonus = (individual_bonus_percent / 100) * bonus_calculation_amount
				if bonus_calculation_amount and department_bonus_percent:
					entry.department_bonus = (department_bonus_percent / 100) * bonus_calculation_amount

			# Rule: Individual-only path
			# - Award ONLY INDIVIDUAL bonus when individual_score_value > min_individual_score_for_bonus and department_score_value < min_avg_score_for_bonus
			elif entry.individual_score_value > nv_setting_doc.min_individual_score_for_bonus  and entry.department_score_value < nv_setting_doc.min_avg_score_for_bonus:
				# if bonus_calculation_amount and department_bonus_percent:
				# 	entry.department_bonus = (department_bonus_percent / 100) * bonus_calculation_amount
				if bonus_calculation_amount and individual_bonus_percent:
					entry.individual_bonus = (individual_bonus_percent / 100) * bonus_calculation_amount

			entry.total_bonus = entry.individual_bonus + entry.department_bonus + entry.company_bonus

	def on_submit(self):
		self.create_additional_salaries()

	@frappe.whitelist()
	def create_additional_salaries(self):
		if not self.appraisal_payout_details:
			return

		for entry in self.appraisal_payout_details:
			if entry.individual_bonus:
				salary_component = "Bonus Individual"
				if self.payout_frequency == "Quarterly":
					salary_component = "Bonus Individual (Quarterly)"
				elif self.payout_frequency == "Annually":
					salary_component = "Bonus Individual (Annual)"
				create_additional_salaries(entry.employee, salary_component, entry.individual_bonus, self.posting_date)

			if entry.department_bonus:
				salary_component = "Bonus Department"
				if self.payout_frequency == "Quarterly":
					salary_component = "Bonus Department (Quarterly)"
				elif self.payout_frequency == "Annually":
					salary_component = "Bonus Department (Annual)"
				create_additional_salaries(entry.employee, salary_component, entry.department_bonus, self.posting_date)

			if entry.company_bonus:
				salary_component = "Bonus Company"
				if self.payout_frequency == "Quarterly":
					salary_component = "Bonus Company (Quarterly)"
				elif self.payout_frequency == "Annually":
					salary_component = "Bonus Company (Annual)"
				create_additional_salaries(entry.employee, salary_component, entry.company_bonus, self.posting_date)
		
		frappe.msgprint(_("Additional Salary created based on Appraisal Payout"))

def create_additional_salaries(employee, salary_component, amount, payroll_date):
	relieving_date = frappe.db.get_value("Employee", employee, "relieving_date")
	doc = frappe.get_doc({
		'doctype': 'Additional Salary',
		'employee': employee,
		'salary_component': salary_component,
		'amount': amount,
		'payroll_date': relieving_date if relieving_date and str(relieving_date) < payroll_date else payroll_date.__str__()
	})
	doc.insert()

def get_emp_list(cond):
		return frappe.db.sql(
			"""
				select
					distinct t1.name as employee, t1.employee_name, t1.department, t1.designation, t1.grade, t1.relieving_date
				from
					`tabEmployee` t1
				where
					t1.status != 'Inactive'
			%s
			"""
			% cond,
			as_dict=True,
		)

def get_filter_condition(filters):
	cond = ""
	for f in ["company", "branch", "department", "designation", "grade"]:
		if filters.get(f):
			cond += " and t1." + f + " = " + frappe.db.escape(filters.get(f))

	return cond
	
def get_base_from_most_recent_salary_structure_assignment(employee):
	salary_structure_assignment = DocType('Salary Structure Assignment')
	base = (frappe.qb.from_(salary_structure_assignment)
		 .select(salary_structure_assignment.base)
		 .where(
			 (salary_structure_assignment.employee == employee)
			 & (salary_structure_assignment.docstatus == 1)
		 )
		 .orderby(salary_structure_assignment.from_date, order = Order.desc)
		 .limit(1)
		 ).run(as_list = True)
	
	return base[0][0] if base else 0