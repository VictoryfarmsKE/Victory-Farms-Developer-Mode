import hashlib
import inspect

import frappe
import requests
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from frappe import _
from frappe.utils import cint

EXPECTED_SOURCE_SHA256 = "6b7a18ce210b05b80a0d2d75937dfc02c3aad5668c5c897cabc9024f528fbdfa"
TIMEOUT_LIMITS = {
	"custom_mpesa_connect_timeout": {"label": "M-Pesa Connect Limit", "default": 10, "min": 3, "max": 10},
	"custom_mpesa_read_timeout": {"label": "M-Pesa Reply Limit", "default": 30, "min": 10, "max": 40},
}
original_create_payment_request = POSInvoice.create_payment_request


def configured_timeout(fieldname):
	limit = TIMEOUT_LIMITS[fieldname]
	seconds = cint(frappe.db.get_single_value("POS Settings", fieldname))
	if not seconds:
		return limit["default"]
	return min(max(seconds, limit["min"]), limit["max"])


def mpesa_timeout():
	return (
		configured_timeout("custom_mpesa_connect_timeout"),
		configured_timeout("custom_mpesa_read_timeout"),
	)


def validate_pos_settings(doc, method=None):
	if not any(doc.has_value_changed(fieldname) for fieldname in TIMEOUT_LIMITS):
		return
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only a System Manager can change the M-Pesa limits."))
	for fieldname, limit in TIMEOUT_LIMITS.items():
		seconds = cint(doc.get(fieldname))
		if seconds and not limit["min"] <= seconds <= limit["max"]:
			frappe.throw(
				_("{0} must be between {1} and {2} seconds, or 0 to use {3} seconds.").format(
					_(limit["label"]), limit["min"], limit["max"], limit["default"]
				)
			)


class TimedRequests:
	def __getattr__(self, name):
		return getattr(requests, name)

	def get(self, url, **kwargs):
		kwargs.setdefault("timeout", mpesa_timeout())
		return requests.get(url, **kwargs)

	def post(self, url, **kwargs):
		kwargs.setdefault("timeout", mpesa_timeout())
		return requests.post(url, **kwargs)


timed_requests = TimedRequests()


@frappe.whitelist()
def create_payment_request(self):
	for pay in self.payments:
		if pay.type == "Phone":
			if pay.amount <= 0:
				frappe.throw(_("Payment amount cannot be less than or equal to 0"))

			if not self.contact_mobile:
				frappe.throw(_("Please enter the phone number first"))

			pay_req = self.get_existing_payment_request(pay) or self.get_new_payment_request(pay)
			try:
				if pay_req.docstatus == 0:
					pay_req.email_to = self.contact_mobile
					pay_req.save()
					frappe.db.commit()
					pay_req.submit()
				else:
					frappe.db.commit()
					pay_req.request_phone_payment()
			except Exception as e:
				if not_responding(e):
					throw_not_responding()
				raise

			return pay_req


def not_responding(exc):
	seen = set()
	while exc is not None and id(exc) not in seen:
		if isinstance(exc, requests.Timeout | requests.ConnectionError):
			return True
		seen.add(id(exc))
		exc = exc.__cause__ or exc.__context__
	return False


def throw_not_responding():
	frappe.local.message_log = []
	frappe.throw(
		_("M-Pesa is not responding right now. Please try again, or ask the customer to pay to the till number."),
		title=_("M-Pesa not responding"),
	)


def mpesa_connector_module():
	try:
		from payments.payment_gateways.doctype.mpesa_settings import mpesa_connector
	except ImportError:
		return None
	return mpesa_connector


def source_sha256():
	return hashlib.sha256(inspect.getsource(original_create_payment_request).encode()).hexdigest()


def source_matches():
	try:
		return source_sha256() == EXPECTED_SOURCE_SHA256
	except (OSError, TypeError):
		return False


def install():
	connector = mpesa_connector_module()
	if connector:
		connector.requests = timed_requests
	if source_matches():
		POSInvoice.create_payment_request = create_payment_request


def is_installed():
	connector = mpesa_connector_module()
	return (connector is None or connector.requests is timed_requests) and (
		POSInvoice.create_payment_request is create_payment_request
	)


def check():
	install()
	if is_installed():
		return []
	problems = [
		"ERPNext POS Invoice create_payment_request changed, M-Pesa prompts hold the Payment Request number again"
	]
	frappe.log_error(title="M-Pesa request check failed", message="\n".join(problems))
	return problems
