// Track recently visited pages and store in localStorage
(function() {
    'use strict';

    const RECENTS_KEY = 'right_hire.recents.v1';
    const MAX_RECENTS = 20;

    function saveRecent(route, doctype, docname) {
        // Get existing recents
        let recents = [];
        try {
            recents = JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]');
        } catch(e) {
            recents = [];
        }

        // Create unique key for this page
        const key = `${doctype}::${docname}`;

        // Remove if already exists (we'll add it to the front)
        recents = recents.filter(r => r.key !== key);

        // Add to front
        recents.unshift({
            key: key,
            route: route,
            doctype: doctype,
            docname: docname,
            timestamp: Date.now()
        });

        // Limit to MAX_RECENTS
        if (recents.length > MAX_RECENTS) {
            recents = recents.slice(0, MAX_RECENTS);
        }

        // Save back
        localStorage.setItem(RECENTS_KEY, JSON.stringify(recents));
    }

    function trackCurrentPage() {
        const route = frappe.get_route();

        // Only track Form pages
        if (route[0] === 'Form' && route[1] && route[2]) {
            const doctype = route[1];
            const docname = route[2];

            // Don't track if it's a new form
            if (docname !== 'new') {
                saveRecent(route, doctype, docname);
            }
        }
    }

    // Track on route change
    if (frappe.router) {
        frappe.router.on('change', function() {
            setTimeout(trackCurrentPage, 300);
        });
    }

    // Track initial page
    $(document).ready(function() {
        setTimeout(trackCurrentPage, 1000);
    });
})();
