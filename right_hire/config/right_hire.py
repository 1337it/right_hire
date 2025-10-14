# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

from frappe import _

def get_data():
    return [
        {
            "label": _("Operations"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Reservation",
                    "description": _("Vehicle Reservations")
                },
                {
                    "type": "doctype",
                    "name": "Rental Agreement",
                    "description": _("Active Rental Agreements")
                },
                {
                    "type": "doctype",
                    "name": "Lease Contract",
                    "description": _("Long-term Lease Contracts")
                },
                {
                    "type": "doctype",
                    "name": "Vehicle Movement",
                    "description": _("Track Vehicle Movements")
                }
            ]
        },
        {
            "label": _("Fleet Management"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Vehicle",
                    "description": _("Manage Fleet Vehicles")
                },
                {
                    "type": "doctype",
                    "name": "Maintenance Job",
                    "description": _("Vehicle Maintenance")
                },
                {
                    "type": "doctype",
                    "name": "Violation",
                    "description": _("Traffic Violations & Fines")
                },
                {
                    "type": "report",
                    "name": "Fleet Status",
                    "doctype": "Vehicle",
                    "is_query_report": True
                }
            ]
        },
        {
            "label": _("Customers"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Customer",
                    "description": _("Customer Database")
                },
                {
                    "type": "doctype",
                    "name": "Driver",
                    "description": _("Additional Drivers")
                }
            ]
        },
        {
            "label": _("Configuration"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Branch",
                    "description": _("Rental Branches")
                },
                {
                    "type": "doctype",
                    "name": "Parking Lot",
                    "description": _("Parking Locations")
                },
                {
                    "type": "doctype",
                    "name": "Rate Plan",
                    "description": _("Pricing Plans")
                },
                {
                    "type": "doctype",
                    "name": "Insurance Policy",
                    "description": _("Insurance Policies")
                }
            ]
        },
        {
            "label": _("Financial"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Invoice",
                    "description": _("Invoices")
                },
                {
                    "type": "report",
                    "name": "Revenue Analysis",
                    "doctype": "Rental Agreement",
                    "is_query_report": True
                }
            ]
        },
        {
            "label": _("Reports"),
            "items": [
                {
                    "type": "report",
                    "name": "Vehicle Utilization",
                    "doctype": "Vehicle",
                    "is_query_report": True
                },
                {
                    "type": "report",
                    "name": "Revenue Analysis",
                    "doctype": "Rental Agreement",
                    "is_query_report": True
                },
                {
                    "type": "report",
                    "name": "Fleet Status",
                    "doctype": "Vehicle",
                    "is_query_report": True
                }
            ]
        }
    ]
