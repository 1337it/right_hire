# Copyright (c) 2024, Tridz Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


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
            "fieldname": "vehicle_id",
            "label": _("Vehicle ID"),
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
            "fieldname": "expiry_type",
            "label": _("Expiry Type"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "expiry_date",
            "label": _("Expiry Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "days_remaining",
            "label": _("Days Remaining"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "urgency",
            "label": _("Urgency"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    data = []

    # Get all vehicles
    vehicles = frappe.db.sql("""
        SELECT
            name as vehicle,
            vehicle_id,
            CONCAT(IFNULL(make, ''), ' ', IFNULL(model, '')) as make_model,
            registration_expiry,
            insurance_expiry,
            next_service_due,
            status
        FROM
            `tabVehicle`
        WHERE
            docstatus < 2
    """, as_dict=1)

    for vehicle in vehicles:
        # Check registration expiry
        if vehicle.registration_expiry:
            days = date_diff(vehicle.registration_expiry, today())
            if days <= 90:  # Show if expiring within 90 days or overdue
                data.append({
                    "vehicle": vehicle.vehicle,
                    "vehicle_id": vehicle.vehicle_id,
                    "make_model": vehicle.make_model,
                    "expiry_type": "Registration",
                    "expiry_date": vehicle.registration_expiry,
                    "days_remaining": days,
                    "urgency": get_urgency(days),
                    "status": vehicle.status
                })

        # Check insurance expiry
        if vehicle.insurance_expiry:
            days = date_diff(vehicle.insurance_expiry, today())
            if days <= 90:  # Show if expiring within 90 days or overdue
                data.append({
                    "vehicle": vehicle.vehicle,
                    "vehicle_id": vehicle.vehicle_id,
                    "make_model": vehicle.make_model,
                    "expiry_type": "Insurance",
                    "expiry_date": vehicle.insurance_expiry,
                    "days_remaining": days,
                    "urgency": get_urgency(days),
                    "status": vehicle.status
                })

        # Check service due
        if vehicle.next_service_due:
            days = date_diff(vehicle.next_service_due, today())
            if days <= 30:  # Show if service due within 30 days or overdue
                data.append({
                    "vehicle": vehicle.vehicle,
                    "vehicle_id": vehicle.vehicle_id,
                    "make_model": vehicle.make_model,
                    "expiry_type": "Service Due",
                    "expiry_date": vehicle.next_service_due,
                    "days_remaining": days,
                    "urgency": get_urgency(days),
                    "status": vehicle.status
                })

    # Sort by urgency (overdue first, then by days remaining)
    data.sort(key=lambda x: (x["urgency"] != "Overdue", x["days_remaining"]))

    return data


def get_urgency(days_remaining):
    """Calculate urgency level based on days remaining"""
    if days_remaining < 0:
        return "Overdue"
    elif days_remaining <= 7:
        return "Critical"
    elif days_remaining <= 14:
        return "High"
    elif days_remaining <= 30:
        return "Medium"
    else:
        return "Low"
