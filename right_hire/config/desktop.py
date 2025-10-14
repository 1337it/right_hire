# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

from frappe import _

def get_data():
    return [
        {
            "module_name": "Right Hire",
            "category": "Modules",
            "label": _("Right Hire"),
            "color": "#FF5733",
            "icon": "octicon octicon-package",
            "type": "module",
            "description": _("Car Rental & Lease Management System")
        }
    ]
