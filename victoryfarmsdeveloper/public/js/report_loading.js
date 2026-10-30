(() => {
	const POLL_SECONDS = 10;
	const MAKE_METHOD = "frappe.core.doctype.prepared_report.prepared_report.make_prepared_report";
	const RUNNING_METHOD = "victoryfarmsdeveloper.setup.report_runs.running_prepared_report";
	const STATUS_METHOD = "victoryfarmsdeveloper.setup.report_runs.prepared_report_status";

	const loader_html = () => `<div class="msg-box no-border">
			<div class="spinner-border text-muted mb-3" role="status"></div>
			<p>${__("Generating report. This can take a few minutes. It will appear here when ready.")}</p>
		</div>`;

	const set_button_busy = (report, busy) => {
		const button = report.primary_button;
		if (!button) return;
		if (busy) {
			if (!button.data("vf-label")) button.data("vf-label", button.html());
			button
				.prop("disabled", true)
				.html(
					`<span class="spinner-border spinner-border-sm mr-1" role="status"></span>${__(
						"Generating..."
					)}`
				);
			return;
		}
		const label = button.data("vf-label");
		if (label) button.html(label).removeData("vf-label");
		button.prop("disabled", false);
	};

	const show_loader = (report) => {
		report.toggle_report(false);
		report.hide_loading_screen();
		report.toggle_message(true, loader_html());
		set_button_busy(report, true);
	};

	const stop = (report) => {
		if (!report.vf_run) return;
		clearInterval(report.vf_run.timer);
		report.vf_run = null;
		set_button_busy(report, false);
	};

	const check = (report, name) =>
		frappe.xcall(STATUS_METHOD, { name }).then((status) => {
			if (report.vf_run?.name !== name) return;
			if (status === "Queued" || status === "Started") return;
			stop(report);
			if (status === "Completed") return report.refresh();
			if (status === "Error") {
				report.toggle_message(
					true,
					__("The report could not be generated. Check the filters and try again.")
				);
				frappe.show_alert(
					{ message: __("Report {0} failed", [__(report.report_name)]), indicator: "red" },
					10
				);
				return;
			}
			report.toggle_nothing_to_show(true);
		});

	const watch = (report, name) => {
		stop(report);
		report.prepared_report_doc_name = name;
		report.vf_run = { name, timer: setInterval(() => check(report, name), POLL_SECONDS * 1000) };
		show_loader(report);
	};

	const resume = (report) => {
		if (!report.prepared_report || report.prepared_report_document || report.prepared_report_name) return;
		if (report.vf_run) return;
		const report_name = report.report_name;
		const filters = report.get_filter_values(false);
		return frappe.xcall(RUNNING_METHOD, { report_name, filters }).then((name) => {
			if (!name || report.vf_run || report.report_name !== report_name) return;
			watch(report, name);
		});
	};

	const patch = () => {
		const proto = frappe.views?.QueryReport?.prototype;
		if (!proto || proto.vf_loading) return;
		proto.vf_loading = true;

		const refresh = proto.refresh;
		proto.refresh = function (...args) {
			stop(this);
			const result = refresh.apply(this, args);
			result?.then?.(() => resume(this));
			return result;
		};

		const toggle_primary_button_disabled = proto.toggle_primary_button_disabled;
		proto.toggle_primary_button_disabled = function (disable) {
			if (!disable && this.vf_run) return;
			return toggle_primary_button_disabled.call(this, disable);
		};

		const toggle_nothing_to_show = proto.toggle_nothing_to_show;
		proto.toggle_nothing_to_show = function (flag) {
			if (flag && this.vf_run) return show_loader(this);
			const result = toggle_nothing_to_show.call(this, flag);
			if (flag && this.prepared_report && !this.prepared_report_document) {
				this.toggle_message(
					true,
					__("Set the filters and click {0}.", [__("Generate New Report")])
				);
			}
			return result;
		};

		proto.generate_background_report = function () {
			const missing = this.filters.filter((f) => f.df.reqd && !f.get_value());
			if (missing.length) {
				try {
					this.get_filter_values(true);
				} catch (e) {
					return;
				}
			}
			const filters = this.get_filter_values(true);
			set_button_busy(this, true);
			return frappe
				.xcall(MAKE_METHOD, { report_name: this.report_name, filters })
				.then((data) => {
					frappe.show_alert(
						{
							message: `<a href='/app/prepared-report/${data.name}'>${__(
								"Report initiated, click to view status"
							)}</a>`,
							indicator: "orange",
						},
						10
					);
					watch(this, data.name);
				})
				.catch(() => set_button_busy(this, false));
		};
	};

	patch();
	$(document).on("page-change", patch);
})();
