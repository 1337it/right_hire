frappe.provide("right_hire");

right_hire.utils = {
    check_vehicle_availability: function(vehicle, start_datetime, end_datetime, callback) {
        frappe.call({
            method: "right_hire.api.vehicle.check_availability",
            args: {vehicle: vehicle, start_datetime: start_datetime, end_datetime: end_datetime},
            callback: function(r) { if (callback) callback(r.message); }
        });
    }
};

frappe.realtime.on("vehicle_status_changed", function(data) {
    frappe.show_alert({
        message: __("Vehicle {0} status changed to {1}", [data.vehicle, data.status]),
        indicator: 'blue'
    });
});

// Ensure sidebar loads on all pages
(function() {
    'use strict';

    function ensure_sidebar() {
        // Check if sidebar exists
        if ($('.desk-sidebar').length) {
            return;
        }

        // If no sidebar and we're in the desk, try to trigger workspace load
        if (frappe.pages && frappe.pages['Workspaces']) {
            // Workspace page exists, sidebar should load
            return;
        }

        // Preload workspace to ensure sidebar is created
        if (frappe.views && frappe.views.pageview) {
            try {
                frappe.views.pageview.with_page('Workspaces', function() {
                    // Workspace loaded
                });
            } catch (e) {
                // Ignore errors
                console.log('[Right Hire] Workspace preload skipped');
            }
        }
    }

    // Run after frappe is ready
    $(document).ready(function() {
        setTimeout(ensure_sidebar, 2000);
    });

    // Re-check on route changes
    if (frappe.router && frappe.router.on) {
        frappe.router.on('change', function() {
            setTimeout(ensure_sidebar, 1000);
        });
    }
})();
