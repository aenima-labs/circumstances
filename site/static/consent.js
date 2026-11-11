/* Cookie consent: one question, asked once a year.
   The page head sets Google Consent Mode to "denied" and restores an earlier
   "granted". This file shows the banner, records the answer, and tells Tag
   Manager (the Google tag waits for the consent_update event). Any element
   with data-cookie-settings reopens the banner.
   Shared with aenimalabs.com and kodama.house; the only change here is that the
   privacy link comes from <html data-privacy>, because this site lives under a path. */
(function () {
	'use strict';
	var KEY = 'consent', YEAR = 365 * 864e5;
	var PRIVACY = document.documentElement.getAttribute('data-privacy') || '/privacy.html';
	var banner;

	function read() {
		try {
			var c = JSON.parse(localStorage.getItem(KEY) || 'null');
			return c && Date.now() - c.at < YEAR ? c : null;
		} catch (e) { return null; }
	}
	function save(value) {
		try { localStorage.setItem(KEY, JSON.stringify({ analytics: value, at: Date.now() })); } catch (e) {}
	}
	function clearAnalyticsCookies() {
		var host = location.hostname.replace(/^www\./, '');
		document.cookie.split(';').forEach(function (part) {
			var name = part.split('=')[0].trim();
			if (!/^_ga/.test(name)) return;
			['', '; domain=' + host, '; domain=.' + host].forEach(function (d) {
				document.cookie = name + '=; Max-Age=0; path=/' + d;
			});
		});
	}

	function decide(value) {
		var before = read();
		save(value);
		gtag('consent', 'update', { analytics_storage: value });
		if (value === 'granted') {
			window.dataLayer.push({ event: 'consent_update' });
		} else {
			clearAnalyticsCookies();
			// A Google tag that already loaded keeps its state until the next page.
			if (before && before.analytics === 'granted') { location.reload(); return; }
		}
		hide();
	}

	function build() {
		banner = document.createElement('div');
		banner.className = 'cc';
		banner.setAttribute('role', 'dialog');
		banner.setAttribute('aria-label', 'Cookie consent');
		banner.innerHTML =
			'<p class="cc-text"><strong>Analytics, only with your permission.</strong> ' +
			'May we use Google Analytics to see which pages are read? No ads, no tracking across other sites. ' +
			'<a href="' + PRIVACY + '">Privacy</a></p>' +
			'<div class="cc-actions">' +
			'<button type="button" class="cc-btn cc-decline" data-cc="denied">Decline</button>' +
			'<button type="button" class="cc-btn cc-accept" data-cc="granted">Accept</button>' +
			'</div>';
		banner.addEventListener('click', function (e) {
			var b = e.target.closest('[data-cc]');
			if (b) decide(b.getAttribute('data-cc'));
		});
		document.body.appendChild(banner);
	}
	function show() {
		if (!banner) build();
		banner.hidden = false;
		requestAnimationFrame(function () { banner.classList.add('is-open'); });
	}
	function hide() {
		if (!banner) return;
		banner.classList.remove('is-open');
		setTimeout(function () { banner.hidden = true; }, 300);
	}

	document.addEventListener('click', function (e) {
		if (e.target.closest('[data-cookie-settings]')) { e.preventDefault(); show(); }
	});
	if (!read()) show();
})();
