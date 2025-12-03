# Copyright (c) 2024, Tridz Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)

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
            "fieldname": "purchase_cost",
            "label": _("Purchase Cost"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "current_value",
            "label": _("Current Value"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_revenue",
            "label": _("Total Revenue"),
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
            "fieldname": "net_profit",
            "label": _("Net Profit"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "roi",
            "label": _("ROI %"),
            "fieldtype": "Percent",
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
    conditions = ""

    if filters and filters.get("branch"):
        conditions += " AND v.branch = %(branch)s"

    if filters and filters.get("status"):
        conditions += " AND v.status = %(status)s"

    query = f"""
        SELECT
            v.name as vehicle,
            v.vehicle_id,
            CONCAT(IFNULL(v.make, ''), ' ', IFNULL(v.model, '')) as make_model,
            IFNULL(v.purchase_cost, 0) as purchase_cost,
            IFNULL(v.current_book_value, 0) as current_value,
            IFNULL(v.total_revenue, 0) as total_revenue,
            IFNULL(v.total_maintenance_cost, 0) as maintenance_cost,
            IFNULL(v.net_profit, 0) as net_profit,
            CASE
                WHEN IFNULL(v.purchase_cost, 0) > 0
                THEN (IFNULL(v.net_profit, 0) / v.purchase_cost) * 100
                ELSE 0
            END as roi,
            v.status
        FROM
            `tabVehicle` v
        WHERE
            v.docstatus < 2
            {conditions}
        ORDER BY
            net_profit DESC
    """

    data = frappe.db.sql(query, filters, as_dict=1)

    return data


def get_chart(data):
    if not data:
        return None

    # Get top 10 by net profit
    top_10 = data[:10]

    labels = [d.get("vehicle_id") or d.get("vehicle") for d in top_10]
    profits = [d.get("net_profit") or 0 for d in top_10]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Net Profit",
                    "values": profits
                }
            ]
        },
        "type": "bar",
        "colors": ["#28a745"]
    }
