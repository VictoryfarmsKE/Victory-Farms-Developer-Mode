/**
 * Site-wide idle-session warning.
 *
 * Server-side enforcement lives in System Settings > Session Expiry
 * (see victoryfarmsdeveloper/setup/session_security.py), which is the real
 * security backstop: it rejects stale sessions regardless of what happens
 * here. This script only adds the part the server can't do on its own --
 * proactively warning the user and clearing the screen before that cutoff,
 * instead of leaving a stale screen visible until the next API call fails.
 *
 * TEST_MODE mirrors victoryfarmsdeveloper/setup/session_security.py.
 * Flip both together when moving from testing to the production policy.
 */
(() => {
	if (window.vf_idle_session_warning_installed) return;
	window.vf_idle_session_warning_installed = true;

	// ---- Configuration -------------------------------------------------
	const TEST_MODE = true;
	const SESSION_EXPIRY_MINUTES = TEST_MODE ? 15 : 120;
	const WARNING_LEAD_MINUTES = TEST_MODE ? 5 : 15;
	const CRITICAL_SECONDS = 60; // last minute: animation speeds up, turns red

	const EXPIRY_MS = SESSION_EXPIRY_MINUTES * 60 * 1000;
	const WARNING_MS = WARNING_LEAD_MINUTES * 60 * 1000;
	const WARN_AFTER_MS = EXPIRY_MS - WARNING_MS;

	let idleTimer = null;
	let countdownInterval = null;
	let overlay = null;
	let expiresAt = null;

	function buildOverlay() {
		if (overlay) return overlay;
		overlay = document.createElement("div");
		overlay.className = "vf-idle-overlay";
		overlay.innerHTML = `
			<div class="vf-idle-modal" role="alertdialog" aria-live="assertive">
				<div class="vf-idle-fish-wrap">
					<svg class="vf-idle-fish" viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg">
						<path class="vf-fish-tail" d="M8 40 L28 24 L28 56 Z"></path>
						<path class="vf-fish-body" d="M28 40c0-15 18-26 40-26 16 0 30 8 38 20 2 3 2 9 0 12-8 12-22 20-38 20-22 0-40-11-40-26z"></path>
						<path class="vf-fish-fin" d="M62 16c4-8 14-10 20-6-4 6-10 10-16 12z"></path>
						<circle class="vf-fish-eye-white" cx="90" cy="34" r="4.5"></circle>
						<circle class="vf-fish-eye-pupil" cx="91.5" cy="34" r="2"></circle>
					</svg>
					<svg class="vf-idle-watch" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
						<circle class="vf-watch-pulse" cx="20" cy="20" r="17"></circle>
						<circle class="vf-watch-face" cx="20" cy="20" r="14"></circle>
						<rect class="vf-watch-loop" x="17" y="1" width="6" height="5" rx="1.5"></rect>
						<line class="vf-watch-hand-hour" x1="20" y1="20" x2="20" y2="11"></line>
						<line class="vf-watch-hand-second" x1="20" y1="20" x2="27" y2="20"></line>
						<circle class="vf-watch-center" cx="20" cy="20" r="1.4"></circle>
					</svg>
				</div>
				<h3 class="vf-idle-title">${__("Still there?")}</h3>
				<p class="vf-idle-message">${__("You've been inactive. For security, you'll be logged out in")} <span class="vf-idle-countdown">--:--</span>.</p>
				<div class="vf-idle-actions">
					<button type="button" class="btn btn-primary btn-sm vf-idle-stay">${__("Stay logged in")}</button>
					<button type="button" class="btn btn-default btn-sm vf-idle-logout">${__("Log out now")}</button>
				</div>
			</div>
		`;
		document.body.appendChild(overlay);
		overlay.querySelector(".vf-idle-stay").addEventListener("click", onUserStillHere);
		overlay.querySelector(".vf-idle-logout").addEventListener("click", () => frappe.app.logout());
		return overlay;
	}

	function showWarning() {
		buildOverlay();
		overlay.classList.add("vf-idle-visible");
		expiresAt = Date.now() + WARNING_MS;
		tickCountdown();
		countdownInterval = setInterval(tickCountdown, 250);
	}

	function hideWarning() {
		if (overlay) overlay.classList.remove("vf-idle-visible", "vf-idle-critical");
		clearInterval(countdownInterval);
		countdownInterval = null;
	}

	function tickCountdown() {
		const remainingMs = expiresAt - Date.now();
		if (remainingMs <= 0) {
			clearInterval(countdownInterval);
			frappe.app.logout();
			return;
		}
		const remainingSec = Math.ceil(remainingMs / 1000);
		const mm = String(Math.floor(remainingSec / 60)).padStart(2, "0");
		const ss = String(remainingSec % 60).padStart(2, "0");
		const el = overlay.querySelector(".vf-idle-countdown");
		if (el) el.textContent = `${mm}:${ss}`;
		overlay.classList.toggle("vf-idle-critical", remainingSec <= CRITICAL_SECONDS);
	}

	function pingServer() {
		// Keep the server-side idle clock (System Settings > Session Expiry)
		// in sync with real activity, not just this client-side timer.
		frappe.call({
			method: "frappe.auth.get_logged_user",
			freeze: false,
			callback: () => {},
			error: () => {},
		});
	}

	function onUserStillHere() {
		pingServer();
		hideWarning();
		resetTimer();
	}

	function resetTimer() {
		clearTimeout(idleTimer);
		idleTimer = setTimeout(showWarning, WARN_AFTER_MS);
	}

	function onActivity() {
		// While the warning is up, only the Stay/Log out buttons should
		// reset things -- otherwise a stray mousemove over the modal itself
		// would silently dismiss a warning the user hasn't acknowledged.
		if (overlay && overlay.classList.contains("vf-idle-visible")) return;
		resetTimer();
	}

	["mousemove", "mousedown", "keydown", "touchstart", "scroll"].forEach((evt) =>
		document.addEventListener(evt, onActivity, { passive: true })
	);

	frappe.ready(resetTimer);
})();
