# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, add_months
from datetime import date


def execute(filters=None):
	columns = get_columns()
	data, summary = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "month", "label": _("Month"), "fieldtype": "Data", "width": 100},
		{"fieldname": "active_leases", "label": _("Active Leases"), "fieldtype": "Int", "width": 100},
		{"fieldname": "lease_income", "label": _("Lease Income"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "active_rentals", "label": _("Active Rentals"), "fieldtype": "Int", "width": 110},
		{"fieldname": "rental_income", "label": _("Rental Income"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_expected", "label": _("Total Expected"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "cumulative", "label": _("Cumulative Total"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "expiring_leases", "label": _("Leases Expiring"), "fieldtype": "Int", "width": 110},
		{"fieldname": "new_leases", "label": _("New Leases Starting"), "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	months_ahead = int(filters.get("months_ahead", 12)) if filters else 12
	today_date = getdate(today())
	start_month = date(today_date.year, today_date.month, 1)

	# Build conditions for filtering
	lease_conditions = "docstatus = 1 AND lease_status IN ('Active', 'Draft')"
	rental_conditions = "docstatus = 1 AND agreement_status NOT IN ('Cancelled', 'Closed')"

	if filters and filters.get("customer"):
		lease_conditions += f" AND customer = {frappe.db.escape(filters['customer'])}"
		rental_conditions += f" AND customer = {frappe.db.escape(filters['customer'])}"

	if filters and filters.get("vehicle"):
		lease_conditions += f" AND vehicle = {frappe.db.escape(filters['vehicle'])}"
		rental_conditions += f" AND vehicle = {frappe.db.escape(filters['vehicle'])}"

	# Get all lease agreements
	leases = frappe.db.sql("""
		SELECT name, vehicle, customer_name, start_date, end_date, monthly_rate
		FROM `tabLease Agreement`
		WHERE {conditions}
	""".format(conditions=lease_conditions), as_dict=1)

	# Get rental agreements (short-term, for current/near-future only)
	rentals = frappe.db.sql("""
		SELECT name, vehicle, DATE(start_datetime) as start_date,
			DATE(IFNULL(end_datetime, start_datetime)) as end_date,
			grand_total, planned_days
		FROM `tabRental Agreement`
		WHERE {conditions}
	""".format(conditions=rental_conditions), as_dict=1)

	# Generate month-by-month forecast
	data = []
	cumulative = 0

	for i in range(months_ahead):
		month_date = add_months_to_date(start_month, i)
		month_end = add_months_to_date(start_month, i + 1)
		from datetime import timedelta
		month_end = month_end - timedelta(days=1)

		month_label = month_date.strftime("%b %Y")

		# Count active leases and income for this month
		active_lease_count = 0
		lease_income = 0
		expiring_count = 0
		new_count = 0

		for l in leases:
			l_start = getdate(l.start_date)
			l_end = getdate(l.end_date)

			# Check if lease is active during this month
			if l_start <= month_end and l_end >= month_date:
				active_lease_count += 1

				# Pro-rate if partial month
				overlap_start = max(l_start, month_date)
				overlap_end = min(l_end, month_end)
				days_in_month = (month_end - month_date).days + 1
				overlap_days = (overlap_end - overlap_start).days + 1
				ratio = overlap_days / days_in_month if days_in_month > 0 else 1

				lease_income += flt(l.monthly_rate) * ratio

			# Check if lease expires this month
			if l_end.year == month_date.year and l_end.month == month_date.month:
				expiring_count += 1

			# Check if lease starts this month
			if l_start.year == month_date.year and l_start.month == month_date.month:
				new_count += 1

		# Count active rentals and income for this month
		active_rental_count = 0
		rental_income = 0

		for r in rentals:
			r_start = getdate(r.start_date)
			r_end = getdate(r.end_date)

			if r_start <= month_end and r_end >= month_date:
				active_rental_count += 1
				total_days = max(1, (r_end - r_start).days + 1)
				overlap_start = max(r_start, month_date)
				overlap_end = min(r_end, month_end)
				overlap_days = (overlap_end - overlap_start).days + 1
				rental_income += flt(r.grand_total) * overlap_days / total_days

		total = flt(lease_income + rental_income, 2)
		cumulative += total

		data.append({
			"month": month_label,
			"active_leases": active_lease_count,
			"lease_income": flt(lease_income, 2),
			"active_rentals": active_rental_count,
			"rental_income": flt(rental_income, 2),
			"total_expected": total,
			"cumulative": flt(cumulative, 2),
			"expiring_leases": expiring_count,
			"new_leases": new_count,
		})

	# Build summary
	total_forecast = cumulative
	avg_monthly = total_forecast / months_ahead if months_ahead > 0 else 0
	summary = [
		{"label": _("Total Forecast"), "value": flt(total_forecast, 2), "datatype": "Currency"},
		{"label": _("Avg Monthly"), "value": flt(avg_monthly, 2), "datatype": "Currency"},
		{"label": _("Active Leases Now"), "value": data[0]["active_leases"] if data else 0, "datatype": "Int"},
		{"label": _("Months Forecast"), "value": months_ahead, "datatype": "Int"},
	]

	return data, summary


def add_months_to_date(d, months):
	"""Add months to a date, returning first of the resulting month"""
	month = d.month + months
	year = d.year + (month - 1) // 12
	month = (month - 1) % 12 + 1
	return date(year, month, 1)


def get_chart(data):
	if not data:
		return None

	labels = [d["month"] for d in data]
	lease_vals = [d["lease_income"] for d in data]
	rental_vals = [d["rental_income"] for d in data]
	cumulative_vals = [d["cumulative"] for d in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": "Lease Income", "values": lease_vals, "chartType": "bar"},
				{"name": "Rental Income", "values": rental_vals, "chartType": "bar"},
				{"name": "Cumulative", "values": cumulative_vals, "chartType": "line"},
			]
		},
		"type": "axis-mixed",
		"colors": ["#4C9AFF", "#28a745", "#ffc107"],
		"height": 350,
		"barOptions": {"stacked": True}
	}
