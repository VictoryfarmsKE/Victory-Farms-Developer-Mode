import hashlib
import importlib
import inspect

import frappe
from erpnext.stock.doctype.warehouse import warehouse

EXPECTED_SOURCE_SHA256 = "41a2e9e34b39487c79126aae019f9edf781c05e248363a77b5ceac710f606cc9"
REPORT_MODULES = (
	"erpnext.stock.report.stock_balance.stock_balance",
	"erpnext.stock.report.stock_ledger.stock_ledger",
	"erpnext.stock.report.stock_analytics.stock_analytics",
	"erpnext.stock.report.stock_ageing.stock_ageing",
	"erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history",
)
original_apply_warehouse_filter = warehouse.apply_warehouse_filter


def apply_warehouse_filter(query, sle, filters):
	names = warehouses_under(filters.get("warehouse"))
	if not names:
		return original_apply_warehouse_filter(query, sle, filters)
	return query.where(sle.warehouse.isin(names))


def warehouses_under(warehouses):
	if not warehouses:
		return []
	if isinstance(warehouses, str):
		warehouses = [warehouses]
	ranges = frappe.get_all(
		"Warehouse", filters={"name": ("in", warehouses)}, fields=["lft", "rgt"], as_list=True
	)
	if not ranges:
		return []
	table = frappe.qb.DocType("Warehouse")
	condition = None
	for lft, rgt in ranges:
		in_range = (table.lft >= lft) & (table.rgt <= rgt)
		condition = in_range if condition is None else condition | in_range
	return frappe.qb.from_(table).select(table.name).where(condition).run(pluck=True)


def report_modules():
	modules = []
	for name in REPORT_MODULES:
		try:
			modules.append(importlib.import_module(name))
		except ImportError:
			continue
	return modules


def source_matches():
	try:
		source = inspect.getsource(original_apply_warehouse_filter)
	except (OSError, TypeError):
		return False
	return hashlib.sha256(source.encode()).hexdigest() == EXPECTED_SOURCE_SHA256


def install():
	if not source_matches():
		return
	warehouse.apply_warehouse_filter = apply_warehouse_filter
	for module in report_modules():
		if getattr(module, "apply_warehouse_filter", None) is original_apply_warehouse_filter:
			module.apply_warehouse_filter = apply_warehouse_filter


def is_installed():
	return warehouse.apply_warehouse_filter is apply_warehouse_filter and all(
		module.apply_warehouse_filter is apply_warehouse_filter for module in report_modules()
	)


def check():
	install()
	if is_installed():
		return []
	problems = [
		"ERPNext apply_warehouse_filter changed, Stock Balance and the other stock reports read every warehouse again"
	]
	frappe.log_error(title="Stock warehouse filter check failed", message="\n".join(problems))
	return problems
