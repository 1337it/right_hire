# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe

def get_notification_config():
    """Return notification configuration"""
    return {
        "for_doctype": {
            "Rental Agreement": {
                "status": "agreement_status"
            },
            "Reservation": {
                "status": "reservation_status"
            },
            "Maintenance Job": {
                "status": "job_status"
            }
        },
        "targets": {
            "Rental Agreement": {
                "filters": [
                    ["agreement_status", "in", ["Active", "Due for Return"]],
                ],
                "fields": ["name", "customer", "vehicle", "end_datetime"],
                "color": "#ff5858"
            },
            "Reservation": {
                "filters": [
                    ["reservation_status", "=", "Confirmed"],
                    ["pickup_datetime", "<=", "Today"]
                ],
                "fields": ["name", "customer", "vehicle"],
                "color": "#ffa00a"
            },
            "Vehicle": {
                "filters": [
                    ["next_service_due", "<=", "Today + 7 days"]
                ],
                "fields": ["name", "plate_no", "next_service_due"],
                "color": "#ffa00a"
            }
        }
    }
