# Copyright (c) 2024, LeetRental and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, flt

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
            "fieldname": "branch",
            "label": _("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "width": 120
        },
        {
            "fieldname": "total_days",
            "label": _("Total Days"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "rented_days",
            "label": _("Rented Days"),
            "fieldtype": "Float",
            "width": 100
        },
        {
            "fieldname": "utilization_pct",
            "label": _("Utilization %"),
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "fieldname": "revenue",
            "label": _("Revenue"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "maintenance_cost",
            "label": _("Maintenance Cost"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "net_revenue",
            "label": _("Net Revenue"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "avg_daily_rate",
            "label": _("Avg Daily Rate"),
            "fieldtype": "Currency",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = []
    values = []
    
    if filters.get("from_date"):
        conditions.append("snapshot_date >= %s")
        values.append(filters.get("from_date"))
    
    if filters.get("to_date"):
        conditions.append("snapshot_date <= %s")
        values.append(filters.get("to_date"))
    
    if filters.get("branch"):
        conditions.append("branch = %s")
        values.append(filters.get("branch"))
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    data = frappe.db.sql(f"""
        SELECT 
            us.vehicle,
            v.plate_no,
            CONCAT(v.make, ' ', v.model) as make_model,
            us.branch,
            COUNT(us.name) as total_days,
            SUM(us.rental_days) as rented_days,
            AVG(us.utilization_pct) as utilization_pct,
            SUM(us.revenue) as revenue,
            SUM(us.maintenance_cost) as maintenance_cost,
            SUM(us.net_revenue) as net_revenue,
            AVG(us.average_daily_rate) as avg_daily_rate
        FROM `tabUtilization Snapshot` us
        INNER JOIN `tabVehicle` v ON us.vehicle = v.name
        WHERE {where_clause}
        GROUP BY us.vehicle
        ORDER BY utilization_pct DESC
    """, tuple(values), as_dict=1)
    
    return data