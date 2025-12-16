// Recent Pages Tracker for Right Hire
// Automatically tracks page visits and stores in localStorage

frappe.provide('righthire.recents');

righthire.recents = {
	init: function() {
		// Track route changes
		frappe.router.on('change', () => {
			this.trackCurrentPage();
		});

		// Track initial page
		setTimeout(() => {
			this.trackCurrentPage();
		}, 1000);
	},

	trackCurrentPage: function() {
		// Get current route
		const route = frappe.get_route();
		if (!route || route.length === 0) return;

		const routeStr = route.join('/');

		// Ignore certain routes
		const ignoreRoutes = ['recents', 'about', 'user', 'workspace', 'print'];
		if (ignoreRoutes.some(r => routeStr.toLowerCase().includes(r.toLowerCase()))) {
			return;
		}

		// Get page information
		let title = document.title.split(' - ')[0];
		let subtitle = '';
		let doctype = '';

		// Extract information based on route type
		if (route[0] === 'List') {
			doctype = route[1];
			title = `${doctype} List`;
			subtitle = 'List View';
		} else if (route[0] === 'Form') {
			doctype = route[1];
			const docname = route[2];
			title = docname;
			subtitle = doctype;
		} else if (route[0] === 'query-report') {
			title = route[1];
			subtitle = 'Report';
		} else if (frappe.pages && frappe.pages[route[0]]) {
			const page = frappe.pages[route[0]];
			title = page.page.title || title;
			subtitle = 'Page';
		}

		// Create recent item
		const recentItem = {
			title: title,
			subtitle: subtitle,
			doctype: doctype,
			route: routeStr,
			timestamp: new Date().toISOString(),
			url: window.location.href
		};

		// Get existing recents
		let recents = JSON.parse(localStorage.getItem('righthire_recents') || '[]');

		// Remove duplicate if exists
		recents = recents.filter(item => item.route !== routeStr);

		// Add new item at the beginning
		recents.unshift(recentItem);

		// Limit to 9 items
		recents = recents.slice(0, 9);

		// Save back to localStorage
		localStorage.setItem('righthire_recents', JSON.stringify(recents));
	},

	clearAll: function() {
		localStorage.removeItem('righthire_recents');
	},

	getRecents: function() {
		return JSON.parse(localStorage.getItem('righthire_recents') || '[]');
	}
};

// Initialize when Frappe is ready
$(document).ready(function() {
	if (frappe.session.user !== 'Guest') {
		righthire.recents.init();
	}
});
