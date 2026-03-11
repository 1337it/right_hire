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
            "fieldname": "name",
            "label": _("Contract"),
            "fieldtype": "Link",
            "options": "Lease to Own",
            "width": 130
        },
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "fieldname": "vehicle",
            "label": _("Vehicle"),
            "fieldtype": "Link",
            "options": "Vehicle",
            "width": 120
        },
        {
            "fieldname": "contract_status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "start_date",
            "fieldtype": "Date",
            "label": _("Start Date"),
            "width": 100
        },
        {
            "fieldname": "end_date",
            "fieldtype": "Date",
            "label": _("End Date"),
            "width": 100
        },
        {
            "fieldname": "monthly_payment",
            "label": _("Monthly Payment"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_amount",
            "label": _("Total Amount"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "amount_paid",
            "label": _("Amount Paid"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "outstanding_amount",
            "label": _("Outstanding"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "payments_remaining",
            "label": _("Payments Left"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "transfer_status",
            "label": _("Transfer Status"),
            "fieldtype": "Data",
            "width": 120
        }
    ]


def get_data(filters):
    conditions = []

    if filters and filters.get("contract_status"):
        conditions.append("contract_status = %(contract_status)s")

    if filters and filters.get("transfer_status"):
        conditions.append("transfer_status = %(transfer_status)s")

    if filters and filters.get("customer"):
        conditions.append("customer = %(customer)s")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            name,
            customer,
            vehicle,
            contract_status,
            start_date,
            end_date,
            monthly_payment,
            total_amount,
            amount_paid,
            outstanding_amount,
            payments_remaining,
            transfer_status
        FROM
            `tabLease to Own`
        WHERE
            docstatus = 1
            AND {where_clause}
        ORDER BY
            start_date DESC
    """

    data = frappe.db.sql(query, filters, as_dict=1)

    return data


def get_chart(data):
    if not data:
        return None

    # Group by status
    status_summary = {}
    for row in data:
        status = row.get("contract_status", "Unknown")
        status_summary[status] = status_summary.get(status, 0) + 1

    return {
        "data": {
            "labels": list(status_summary.keys()),
            "datasets": [
                {
                    "name": "Contracts",
                    "values": list(status_summary.values())
                }
            ]
        },
        "type": "bar",
        "colors": ["#4C9AFF"]
    }
