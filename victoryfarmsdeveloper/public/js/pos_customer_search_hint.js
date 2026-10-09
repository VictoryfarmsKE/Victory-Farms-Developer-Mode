frappe.require("point-of-sale.bundle.js", () => {
	const hint = __("Phone (07...) or name / surname");
	const ItemCart = erpnext.PointOfSale && erpnext.PointOfSale.ItemCart;
	if (!ItemCart || ItemCart.prototype.vf_customer_hint) return;
	const make_customer_selector = ItemCart.prototype.make_customer_selector;
	ItemCart.prototype.make_customer_selector = function (...args) {
		const result = make_customer_selector.apply(this, args);
		this.customer_field?.$input?.attr("placeholder", hint);
		return result;
	};
	ItemCart.prototype.vf_customer_hint = true;
	$(".point-of-sale-app .customer-field input").attr("placeholder", hint);
});
