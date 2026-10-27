(() => {
	let background_reports = [];

	const load_background_reports = () =>
		frappe
			.xcall("victoryfarmsdeveloper.setup.report_exports.get_background_reports")
			.then((reports) => {
				background_reports = reports || [];
			});

	const current_report = () => {
		const route = frappe.get_route();
		return route[0] === "query-report" ? route[1] : null;
	};

	const hide_background_box = (dialog) => {
		dialog.set_df_property("export_in_background", "hidden", 1);
	};

	const choose_export_mode = (report_name, values, callback) => {
		const report = frappe.query_report;
		const filters = report.get_filter_values(true);
		if (report.prepared_report_name) filters.prepared_report_name = report.prepared_report_name;
		return frappe
			.xcall("victoryfarmsdeveloper.setup.report_exports.export_mode", {
				report_name,
				filters,
				custom_columns: report.custom_columns?.length ? report.custom_columns : [],
			})
			.then((mode) => callback({ ...values, export_in_background: mode === "background" ? 1 : 0 }));
	};

	const wrap = (utils) => {
		if (!utils || !utils.get_export_dialog || utils.get_export_dialog.vf_background) return;
		const get_export_dialog = utils.get_export_dialog;
		utils.get_export_dialog = function (title, extra_fields, callback) {
			const report_name = current_report();
			const decide = function (values) {
				if (!report_name || !background_reports.includes(report_name)) return callback.call(this, values);
				return choose_export_mode(report_name, values, callback.bind(this));
			};
			const dialog = get_export_dialog.call(this, title, extra_fields, decide);
			if (report_name) {
				if (background_reports.includes(report_name)) hide_background_box(dialog);
				load_background_reports().then(() => {
					if (background_reports.includes(report_name)) hide_background_box(dialog);
				});
			}
			return dialog;
		};
		utils.get_export_dialog.vf_background = true;
		load_background_reports();
	};

	let report_utils = frappe.report_utils;
	wrap(report_utils);
	Object.defineProperty(frappe, "report_utils", {
		configurable: true,
		enumerable: true,
		get: () => report_utils,
		set: (value) => {
			report_utils = value;
			wrap(value);
		},
	});
})();
