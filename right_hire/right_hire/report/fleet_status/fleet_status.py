# Copyright (c) 2024, LeetRental and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart

def get_columns():
    return [
        {
            "fieldname": "vehicle",
            "label": _("Vehicle"),
            "fieldtype": "Link",
            "options": "Vehicle",
            "width": 120
        },
        {
            "fieldname": "plate_no",
            "label": _("Plate No"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "make_model",
            "label": _("Make/Model"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "branch",
            "label": _("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "width": 120
        },
        {
            "fieldname": "odometer",
            "label": _("Odometer (KM)"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "fuel_level",
            "label": _("Fuel Level"),
            "fieldtype": "Percent",
            "width": 100
        },
        {
            "fieldname": "last_service_date",
            "label": _("Last Service"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "next_service_due",
            "label": _("Next Service Due"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "registration_expiry",
            "label": _("Registration Expiry"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "insurance_expiry",
            "label": _("Insurance Expiry"),
            "fieldtype": "Date",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = []
    values = []
    
    if filters.get("branch"):
        conditions.append("branch = %s")
        values.append(filters.get("branch"))
    
    if filters.get("status"):
        conditions.append("status = %s")
        values.append(filters.get("status"))
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    data = frappe.db.sql(f"""
        SELECT 
            name as vehicle,
            plate_no,
            CONCAT(make, ' ', model, ' ', year) as make_model,
            status,
            branch,
            odometer,
            fuel_level,
            last_service_date,
            next_service_due,
            registration_expiry,
            insurance_expiry
        FROM `tabVehicle`
        WHERE {where_clause}
        AND status != 'Deactivated'
        ORDER BY status, plate_no
    """, tuple(values), as_dict=1)
    
    return data

def get_chart_data(data):
    # Count vehicles by status
    status_count = {}
    for row in data:
        status = row.status
        status_count[status] = status_count.get(status, 0) + 1
    
    chart = {
        "data": {
            "labels": list(status_count.keys()),
            "datasets": [
                {
                    "name": "Vehicle Count",
                    "values": list(status_count.values())
                }
            ]
        },
        "type": "donut",
        "height": 300,
        "colors": ["#28a745", "#ffc107", "#17a2b8", "#dc3545", "#6c757d"]
    }
    
    return chart