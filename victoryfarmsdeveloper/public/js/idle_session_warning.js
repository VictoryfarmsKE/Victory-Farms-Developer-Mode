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

	// How often to tell the server "the user is still active" while they're
	// working, so the server's own Session Expiry clock (which only resets
	// on real requests, not on mouse/keyboard activity) doesn't quietly run
	// out before this client-side warning ever gets a chance to show up.
	const KEEPALIVE_INTERVAL_MS = TEST_MODE ? 60 * 1000 : 5 * 60 * 1000;

	let idleTimer = null;
	let countdownInterval = null;
	let overlay = null;
	let expiresAt = null;
	let lastKeepAliveAt = 0;

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
		overlay.querySelector(".vf-idle-logout").addEventListener("click", forceLogout);
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
			forceLogout();
			return;
		}
		const remainingSec = Math.ceil(remainingMs / 1000);
		const mm = String(Math.floor(remainingSec / 60)).padStart(2, "0");
		const ss = String(remainingSec % 60).padStart(2, "0");
		const el = overlay.querySelector(".vf-idle-countdown");
		if (el) el.textContent = `${mm}:${ss}`;
		overlay.classList.toggle("vf-idle-critical", remainingSec <= CRITICAL_SECONDS);
	}

	// Plain fetch() instead of frappe.call() on purpose: frappe.call's default
	// error handling pops up Frappe's own dialogs (session-expired confirm,
	// "Method Not Allowed", etc.), which is exactly the confusing double-popup
	// behaviour we're trying to avoid. Handling the response ourselves keeps
	// this entirely under our control.
	function pingServer(onExpired) {
		fetch("/api/method/frappe.auth.get_logged_user", {
			method: "GET",
			credentials: "same-origin",
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
		})
			.then((res) => {
				if (!res.ok) throw new Error("session expired");
			})
			.catch(() => {
				if (onExpired) onExpired();
			});
	}

	// Logs the user out directly, without Frappe core's "Are you sure you
	// want to log out?" confirmation (frappe.app.logout()) -- that dialog
	// makes sense for a deliberate click, but defeats the purpose of an
	// automatic idle timeout, since by definition no one is there to answer
	// it when it fires.
	function forceLogout() {
		fetch("/api/method/logout", {
			method: "POST",
			credentials: "same-origin",
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
		}).finally(() => {
			window.location.href = "/login";
		});
	}

	function onUserStillHere() {
		hideWarning();
		resetTimer();
		lastKeepAliveAt = Date.now();
		pingServer(forceLogout);
	}

	function resetTimer() {
		clearTimeout(idleTimer);
		idleTimer = setTimeout(showWarning, WARN_AFTER_MS);
	}

	// Called on every detected activity event. Besides resetting the
	// client-side idle timer, this also periodically tells the server the
	// user is still active, so the server's own Session Expiry clock (which
	// only resets on real requests) doesn't drift ahead of and quietly
	// expire before the client-side warning ever gets a chance to show up.
	function maybeKeepAlive() {
		const now = Date.now();
		if (now - lastKeepAliveAt < KEEPALIVE_INTERVAL_MS) return;
		lastKeepAliveAt = now;
		pingServer(forceLogout);
	}

	function onActivity() {
		// While the warning is up, only the Stay/Log out buttons should
		// reset things -- otherwise a stray mousemove over the modal itself
		// would silently dismiss a warning the user hasn't acknowledged.
		if (overlay && overlay.classList.contains("vf-idle-visible")) return;
		resetTimer();
		maybeKeepAlive();
	}

	["mousemove", "mousedown", "keydown", "touchstart", "scroll"].forEach((evt) =>
		document.addEventListener(evt, onActivity, { passive: true })
	);

	frappe.ready(resetTimer);
})();
