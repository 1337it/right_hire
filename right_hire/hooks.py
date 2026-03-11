app_name = "right_hire"
app_title = "Right Hire"
app_publisher = "Right Hire"
app_description = "Comprehensive Car Rental & Lease Management System"
app_email = "support@righthire.com"
app_license = "MIT"
app_version = "1.0.0"

app_include_css = [
	"/assets/right_hire/css/right_hire.css",
	"/assets/right_hire/css/portal-settings.css",
	# "/assets/right_hire/css/minimize-to-sidebar.css",  # Removed - minimize to sidebar disabled
	"/assets/right_hire/css/hide_minidock.css",
	# "/assets/right_hire/css/sidebar_toggle.css",  # Removed - collapsible sidebar disabled
	"/assets/right_hire/css/icons.css"
]

app_include_js = [
	"/assets/right_hire/js/right_hire.js",
	"/assets/right_hire/js/portal-settings.js",
	# "/assets/right_hire/js/minimize-to-sidebar.js",  # Removed - minimize to sidebar disabled
	"/assets/right_hire/js/enter-to-next-and-focus-first.js",
	"/assets/right_hire/js/advanced_link_picker.js",
	# "/assets/right_hire/js/sidebar_toggle.js",  # Removed - collapsible sidebar disabled
	"/assets/right_hire/js/sidebar_accordion.js",
	"/assets/right_hire/js/icon_sets.js",
	"/assets/right_hire/js/icons.js",
	"/assets/right_hire/js/vehicle_listview.js",
	"/assets/right_hire/js/reservation.js",
	"/assets/right_hire/js/vehicle.js",
	"/assets/right_hire/js/navbar_back_button.js",
	"/assets/right_hire/js/track_recents.js"
]

# include js in doctype views
doctype_js = {
    "Vehicle": "public/js/vehicle.js",
    "Reservation": "public/js/reservation.js",
    "Lease Contract": "public/js/lease_contract.js",
    "Customer": "right_hire/doctype/customer/customer.js"
}

# Role-based home pages
role_home_page = {
    "Customer": "/portal",
}

# Installation
after_install = "right_hire.setup.install.after_install"
after_migrate = "right_hire.setup.install.after_migrate"

# Apply monkey patches on app load
boot_session = "right_hire.patches.fix_party_sales_team.apply_patch"

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
        "on_cancel": "right_hire.right_hire.doctype.rental_agreement.rental_agreement.on_agreement_cancel",
        "before_submit": [
            "right_hire.right_hire.salik_integration.sync_before_contract_closure",
            "right_hire.right_hire.darb_integration.sync_before_contract_closure",
            "right_hire.right_hire.rta_fines_integration.sync_before_contract_closure"
        ]
    },
    "Lease Contract": {
        "before_submit": [
            "right_hire.right_hire.salik_integration.sync_before_contract_closure",
            "right_hire.right_hire.darb_integration.sync_before_contract_closure",
            "right_hire.right_hire.rta_fines_integration.sync_before_contract_closure"
        ]
    },
    "Reservation": {
        "validate": "right_hire.right_hire.doctype.reservation.reservation.validate_reservation",
        "on_update": "right_hire.right_hire.doctype.reservation.reservation.check_conflicts"
    },
    "Sales Invoice": {
        "before_insert": "right_hire.right_hire.invoice_defaults.set_invoice_defaults"
    }
}

# Scheduled Tasks
scheduler_events = {
    "hourly": [
        "right_hire.tasks.hourly.check_reservation_conflicts",
        "right_hire.tasks.hourly.check_overdue_returns",
        "right_hire.tasks.hourly.sync_all_apis",  # Salik + Darb + RTA fines (5 AM - 6 PM UAE only)
    ],
    "daily": [
        "right_hire.tasks.daily.calculate_daily_utilization",
        "right_hire.tasks.daily.send_expiry_alerts",
        "right_hire.tasks.daily.check_maintenance_due",
        "right_hire.right_hire.rta_vehicle_sync.sync_vehicles_from_rta",
        "right_hire.right_hire.doctype.lease_agreement.lease_agreement.auto_create_lease_invoices"
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
# Note: Workspace removed from fixtures to allow UI editing without revert on migrate
# To export workspace changes to code: bench export-fixtures --app right_hire --doctype Workspace
fixtures = [
    # Export all custom fields with module = Right Hire (this now includes ERPNext doctype custom fields)
    {"dt": "Custom Field", "filters": [["module", "=", "Right Hire"]]},
    {"dt": "Role", "filters": [["name", "in", [
        "Fleet Manager", "Counter Agent", "Fleet Ops", "Mechanic", "Right Hire Admin"
    ]]]},
    # Dashboard Number Cards
    {"dt": "Number Card", "filters": [["module", "=", "Right Hire"]]},
    # Dashboard Charts
    {"dt": "Dashboard Chart", "filters": [["module", "=", "Right Hire"]]},
    # Custom HTML Blocks for workspace widgets
    {"dt": "Custom HTML Block", "filters": [["name", "=", "API Status Dashboard"]]},
    # Property Setters for Sales Invoice field customization
    {"dt": "Property Setter", "filters": [["doc_type", "=", "Sales Invoice"], ["module", "=", "Right Hire"]]},
    # {"dt": "Workspace", "filters": [["module", "=", "Right Hire"]]},  # Removed - edit via UI
]
