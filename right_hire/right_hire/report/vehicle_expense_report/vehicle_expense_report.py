# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)

	return columns, data, None, chart


def get_columns():
	"""Return report columns"""
	return [
		{
			"fieldname": "expense_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "vehicle",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Vehicle",
			"width": 200
		},
		{
			"fieldname": "expense_type",
			"label": _("Expense Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "supplier_name",
			"label": _("Supplier"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "amount_before_vat",
			"label": _("Amount (Excl. VAT)"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount"),
			"fieldtype": "Currency",
			"width": 110
		},
		{
			"fieldname": "total_amount",
			"label": _("Total Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 90
		},
		{
			"fieldname": "odometer_reading",
			"label": _("Odometer (KM)"),
			"fieldtype": "Int",
			"width": 110
		},
		{
			"fieldname": "name",
			"label": _("Expense ID"),
			"fieldtype": "Link",
			"options": "Vehicle Expense",
			"width": 130
		}
	]


def get_data(filters):
	"""Get expense data based on filters"""
	conditions = get_conditions(filters)

	data = frappe.db.sql(f"""
		SELECT
			ve.expense_date,
			ve.vehicle,
			ve.expense_type,
			ve.supplier_name,
			ve.amount_before_vat,
			ve.vat_amount,
			ve.total_amount,
			ve.status,
			ve.odometer_reading,
			ve.name
		FROM
			`tabVehicle Expense` ve
		WHERE
			ve.docstatus < 2
			{conditions}
		ORDER BY
			ve.expense_date DESC, ve.vehicle
	""", filters, as_dict=1)

	return data


def get_conditions(filters):
	"""Build WHERE conditions from filters"""
	conditions = []

	if filters.get("from_date"):
		conditions.append("ve.expense_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("ve.expense_date <= %(to_date)s")

	if filters.get("vehicle"):
		conditions.append("ve.vehicle = %(vehicle)s")

	if filters.get("expense_type"):
		conditions.append("ve.expense_type = %(expense_type)s")

	if filters.get("status"):
		conditions.append("ve.status = %(status)s")

	if filters.get("supplier"):
		conditions.append("ve.supplier = %(supplier)s")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data):
	"""Generate chart data for visualization"""
	if not data:
		return None

	# Group by expense type
	expense_by_type = {}
	for row in data:
		expense_type = row.get("expense_type") or "Other"
		if expense_type not in expense_by_type:
			expense_by_type[expense_type] = 0
		expense_by_type[expense_type] += flt(row.get("total_amount"))

	# Sort by amount
	sorted_expenses = sorted(expense_by_type.items(), key=lambda x: x[1], reverse=True)

	return {
		"data": {
			"labels": [x[0] for x in sorted_expenses],
			"datasets": [
				{
					"name": "Total Amount",
					"values": [x[1] for x in sorted_expenses]
				}
			]
		},
		"type": "bar",
		"colors": ["#27AE60"]
	}
