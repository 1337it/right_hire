app_name = "right_hire"
app_title = "Right Hire"
app_publisher = "Right Hire"
app_description = "Comprehensive Car Rental & Lease Management System"
app_email = "support@righthire.com"
app_license = "MIT"
app_version = "1.0.0"

# Includes in 
.DS_Store
hi
yesterday
__init__.py
hi
yesterday
advanced_link_picker.js
hi
yesterday
customer_quick_scan.js
hi
yesterday
enter-to-next-and-focus-first.js
hi
yesterday
icons.js
hi
yesterday
minimize-to-sidebar.js
hi
yesterday
portal-settings.js
hi
yesterday
rental_agreement.js
hi
yesterday
reservation.js
hi
yesterday
right_hire.js
hi
yesterday
sidebar_toggle.js
hi
yesterday
vehicle.js
hi
yesterday
vehicle_listview.js

app_include_css = [
	"/assets/leetrental/css/right_hire.css",
	"/assets/leetrental/css/portal-settings.css",
	"/assets/leetrental/css/minimize-to-sidebar.css",
	"/assets/leetrental/css/sidebar_toggle.css",
	"/assets/leetrental/css/icons.css"
]

app_include_js = [
	"/assets/leetrental/js/right_hire.js",
	"/assets/leetrental/js/portal-settings.js",
	"/assets/leetrental/js/minimize-to-sidebar.js",
	"/assets/leetrental/js/customer_quick_scan.js",
	"/assets/leetrental/js/enter-to-next-and-focus-first.js",
	"/assets/leetrental/js/advanced_link_picker.js",
	"/assets/leetrental/js/sidebar_toggle.js",
	"/assets/leetrental/js/icons.js",
	"/assets/leetrental/js/vehicle_listview.js",
	"/assets/leetrental/js/reservation.js",
	"/assets/leetrental/js/vehicle.js",
	"/assets/leetrental/js/vehicle_listview.js"
]

# include js in doctype views
doctype_js = {
    "Vehicle": "public/js/vehicle.js",
    "Reservation": "public/js/reservation.js",
    "Rental Agreement": "public/js/rental_agreement.js",
    "Lease Contract": "public/js/lease_contract.js"
}

# Installation
after_install = "right_hire.setup.install.after_install"

# Desk Notifications
notification_config = "right_hire.notifications.get_notification_config"

# Document Events
doc_events = {
    "Vehicle": {
        "validate": "right_hire.right_hire.doctype.vehicle.vehicle.validate_vehicle",
        "on_update": "right_hire.right_hire.doctype.vehicle.vehicle.on_vehicle_update"
    },
    "Rental Agreement": {
        "validate": "right_hire.right_hire.doctype.rental_agreement.rental_agreement.validate_agreement",
        "on_submit": "right_hire.right_hire.doctype.rental_agreement.rental_agreement.on_agreement_submit",
        "on_cancel": "right_hire.right_hire.doctype.rental_agreement.rental_agreement.on_agreement_cancel"
    },
    "Reservation": {
        "validate": "right_hire.right_hire.doctype.reservation.reservation.validate_reservation",
        "on_update": "right_hire.right_hire.doctype.reservation.reservation.check_conflicts"
    }
}

# Scheduled Tasks
scheduler_events = {
    "hourly": [
        "right_hire.tasks.hourly.check_reservation_conflicts",
        "right_hire.tasks.hourly.check_overdue_returns"
    ],
    "daily": [
        "right_hire.tasks.daily.calculate_daily_utilization",
        "right_hire.tasks.daily.send_expiry_alerts",
        "right_hire.tasks.daily.check_maintenance_due"
    ],
    "weekly": [
        "right_hire.tasks.weekly.generate_utilization_report"
    ],
    "monthly": [
        "right_hire.tasks.monthly.generate_lease_invoices",
        "right_hire.tasks.monthly.calculate_profitability"
    ]
}

# Fixtures
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Right Hire"]]},
    {"dt": "Role", "filters": [["name", "in", [
        "Fleet Manager", "Counter Agent", "Fleet Ops", "Mechanic", "Right Hire Admin"
    ]]]},
    {"dt": "Workspace", "filters": [["module", "=", "Right Hire"]]}
]
