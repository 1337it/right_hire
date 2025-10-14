# Copyright (c) 2024, LeetRental and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(data, filters)
    return columns, data, None, chart

def get_columns(filters):
    columns = [
        {
            "fieldname": "period",
            "label": _("Period"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "total_agreements",
            "label": _("Total Agreements"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "total_revenue",
            "label": _("Total Revenue"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "rental_revenue",
            "label": _("Rental Revenue"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "extras_revenue",
            "label": _("Extras Revenue"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "overage_revenue",
            "label": _("Overage Revenue"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "avg_agreement_value",
            "label": _("Avg Agreement Value"),
            "fieldtype": "Currency",
            "width": 150
        }
    ]
    
    if filters.get("group_by") == "Branch":
        columns.insert(1, {
            "fieldname": "branch",
            "label": _("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "width": 120
        })
    
    return columns

def get_data(filters):
    conditions = []
    values = []
    
    if filters.get("from_date"):
        conditions.append("DATE(start_datetime) >= %s")
        values.append(filters.get("from_date"))
    
    if filters.get("to_date"):
        conditions.append("DATE(start_datetime) <= %s")
        values.append(filters.get("to_date"))
    
    if filters.get("branch"):
        conditions.append("branch = %s")
        values.append(filters.get("branch"))
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    group_by = filters.get("group_by", "Month")
    
    if group_by == "Month":
        date_format = "DATE_FORMAT(start_datetime, '%%Y-%%m')"
    elif group_by == "Week":
        date_format = "DATE_FORMAT(start_datetime, '%%Y-W%%u')"
    elif group_by == "Day":
        date_format = "DATE(start_datetime)"
    elif group_by == "Branch":
        date_format = "branch"
    else:
        date_format = "DATE_FORMAT(start_datetime, '%%Y-%%m')"
    
    data = frappe.db.sql(f"""
        SELECT 
            {date_format} as period,
            {f"branch," if group_by == "Branch" else ""}
            COUNT(name) as total_agreements,
            SUM(grand_total) as total_revenue,
            SUM(rental_amount) as rental_revenue,
            SUM(
                (SELECT SUM(amount) FROM `tabAgreement Charge` 
                 WHERE parent = `tabRental Agreement`.name 
                 AND charge_type IN ('Extra', 'CDW', 'PAI'))
            ) as extras_revenue,
            SUM(overage_amount) as overage_revenue,
            AVG(grand_total) as avg_agreement_value
        FROM `tabRental Agreement`
        WHERE {where_clause}
        AND agreement_status NOT IN ('Cancelled', 'Draft')
        GROUP BY {date_format} {", branch" if group_by == "Branch" else ""}
        ORDER BY period
    """, tuple(values), as_dict=1)
    
    return data

def get_chart_data(data, filters):
    labels = [d.period for d in data]
    
    datasets = [
        {
            "name": "Total Revenue",
            "values": [d.total_revenue for d in data]
        }
    ]
    
    chart = {
        "data": {
            "labels": labels,
            "datasets": datasets
        },
        "type": "line",
        "height": 300
    }
    
    return chart