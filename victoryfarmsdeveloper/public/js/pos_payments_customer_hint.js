(() => {
	const page = frappe.pages["pos-payments"];
	if (!page || !page.on_page_load || page.vf_customer_hint) return;
	const hint = __("Phone (07...) or name / surname");
	const set_hint = (tries) => {
		const input = window.pr_customer_control && window.pr_customer_control.$input;
		if (input) return input.attr("placeholder", hint);
		if (tries > 0) setTimeout(() => set_hint(tries - 1), 100);
	};
	const on_page_load = page.on_page_load;
	page.on_page_load = function (...args) {
		const result = on_page_load.apply(this, args);
		set_hint(50);
		return result;
	};
	page.vf_customer_hint = true;
	set_hint(0);
})();
