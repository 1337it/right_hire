# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today
from datetime import date


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	return columns, data, None, chart


def get_columns(filters):
	return [
		{"fieldname": "period", "label": _("Period"), "fieldtype": "Data", "width": 120},
		{"fieldname": "lease_count", "label": _("Lease Agreements"), "fieldtype": "Int", "width": 120},
		{"fieldname": "lease_revenue", "label": _("Lease Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "rental_count", "label": _("Rental Agreements"), "fieldtype": "Int", "width": 130},
		{"fieldname": "rental_revenue", "label": _("Rental Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_revenue", "label": _("Total Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "expenses", "label": _("Expenses"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "salik_charges", "label": _("Salik Charges"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "net_revenue", "label": _("Net Revenue"), "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else date(getdate(today()).year, 1, 1)
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else getdate(today())

	group_by = filters.get("group_by", "Month")

	if group_by == "Month":
		date_format = "DATE_FORMAT(%s, '%%Y-%%m')"
	elif group_by == "Quarter":
		date_format = "CONCAT(YEAR(%s), '-Q', QUARTER(%s))"
	elif group_by == "Year":
		date_format = "YEAR(%s)"
	else:
		date_format = "DATE_FORMAT(%s, '%%Y-%%m')"

	# For lease agreements, we recognize revenue monthly based on monthly_rate
	# Generate month periods between from_date and to_date
	periods = generate_periods(from_date, to_date, group_by)

	# Get all active leases in the period
	leases = frappe.db.sql("""
		SELECT name, vehicle, start_date, end_date, monthly_rate, grand_total
		FROM `tabLease Agreement`
		WHERE docstatus = 1
		AND start_date <= %(to_date)s
		AND end_date >= %(from_date)s
		AND lease_status IN ('Active', 'Terminated')
	""", {"from_date": from_date, "to_date": to_date}, as_dict=1)

	# Get rental agreements
	rentals = frappe.db.sql("""
		SELECT name, vehicle, DATE(start_datetime) as start_date,
			DATE(IFNULL(end_datetime, start_datetime)) as end_date, grand_total
		FROM `tabRental Agreement`
		WHERE docstatus = 1
		AND DATE(start_datetime) <= %(to_date)s
		AND DATE(IFNULL(end_datetime, start_datetime)) >= %(from_date)s
		AND agreement_status NOT IN ('Cancelled')
	""", {"from_date": from_date, "to_date": to_date}, as_dict=1)

	# Get expenses by period
	if group_by == "Month":
		exp_group = "DATE_FORMAT(expense_date, '%%Y-%%m')"
	elif group_by == "Quarter":
		exp_group = "CONCAT(YEAR(expense_date), '-Q', QUARTER(expense_date))"
	else:
		exp_group = "YEAR(expense_date)"

	expenses = frappe.db.sql("""
		SELECT {group} as period, SUM(total_amount) as total
		FROM `tabVehicle Expense`
		WHERE docstatus < 2
		AND expense_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY {group}
	""".format(group=exp_group), {"from_date": from_date, "to_date": to_date}, as_dict=1)
	expense_map = {str(e.period): flt(e.total) for e in expenses}

	# Get salik by period
	if group_by == "Month":
		sal_group = "DATE_FORMAT(transaction_date, '%%Y-%%m')"
	elif group_by == "Quarter":
		sal_group = "CONCAT(YEAR(transaction_date), '-Q', QUARTER(transaction_date))"
	else:
		sal_group = "YEAR(transaction_date)"

	salik = frappe.db.sql("""
		SELECT {group} as period, SUM(toll_amount) as total
		FROM `tabSalik Transaction`
		WHERE transaction_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY {group}
	""".format(group=sal_group), {"from_date": from_date, "to_date": to_date}, as_dict=1)
	salik_map = {str(s.period): flt(s.total) for s in salik}

	# Distribute lease revenue across periods
	lease_by_period = {}  # {period: {"count": set(), "revenue": float}}
	for l in leases:
		for period_key, p_start, p_end in periods:
			overlap_start = max(getdate(l.start_date), p_start)
			overlap_end = min(getdate(l.end_date), p_end)
			if overlap_start <= overlap_end:
				if period_key not in lease_by_period:
					lease_by_period[period_key] = {"names": set(), "revenue": 0}
				lease_by_period[period_key]["names"].add(l.name)
				# Calculate days in this period
				days_in_period = (overlap_end - overlap_start).days + 1
				daily_rate = flt(l.monthly_rate) / 30.0
				lease_by_period[period_key]["revenue"] += daily_rate * days_in_period

	# Distribute rental revenue across periods
	rental_by_period = {}
	for r in rentals:
		r_start = getdate(r.start_date)
		r_end = getdate(r.end_date)
		total_days = max(1, (r_end - r_start).days + 1)

		for period_key, p_start, p_end in periods:
			overlap_start = max(r_start, p_start)
			overlap_end = min(r_end, p_end)
			if overlap_start <= overlap_end:
				if period_key not in rental_by_period:
					rental_by_period[period_key] = {"names": set(), "revenue": 0}
				rental_by_period[period_key]["names"].add(r.name)
				days_in_period = (overlap_end - overlap_start).days + 1
				rental_by_period[period_key]["revenue"] += flt(r.grand_total) * days_in_period / total_days

	# Build data rows
	data = []
	for period_key, p_start, p_end in periods:
		lp = lease_by_period.get(period_key, {"names": set(), "revenue": 0})
		rp = rental_by_period.get(period_key, {"names": set(), "revenue": 0})
		lease_rev = flt(lp["revenue"], 2)
		rental_rev = flt(rp["revenue"], 2)
		total_rev = lease_rev + rental_rev
		exp = expense_map.get(period_key, 0)
		sal = salik_map.get(period_key, 0)
		net = total_rev - exp - sal

		data.append({
			"period": period_key,
			"lease_count": len(lp["names"]),
			"lease_revenue": lease_rev,
			"rental_count": len(rp["names"]),
			"rental_revenue": rental_rev,
			"total_revenue": total_rev,
			"expenses": exp,
			"salik_charges": sal,
			"net_revenue": flt(net, 2),
		})

	return data


def generate_periods(from_date, to_date, group_by):
	"""Generate list of (period_key, start_date, end_date) tuples"""
	periods = []
	current = from_date

	if group_by == "Month":
		while current <= to_date:
			year, month = current.year, current.month
			period_key = f"{year:04d}-{month:02d}"
			month_start = date(year, month, 1)
			if month == 12:
				month_end = date(year + 1, 1, 1)
			else:
				month_end = date(year, month + 1, 1)
			month_end = month_end.replace(day=1)
			from datetime import timedelta
			month_end = month_end - timedelta(days=1)
			periods.append((period_key, month_start, month_end))
			# Next month
			if month == 12:
				current = date(year + 1, 1, 1)
			else:
				current = date(year, month + 1, 1)

	elif group_by == "Quarter":
		while current <= to_date:
			year = current.year
			quarter = (current.month - 1) // 3 + 1
			period_key = f"{year}-Q{quarter}"
			q_start = date(year, (quarter - 1) * 3 + 1, 1)
			if quarter == 4:
				q_end = date(year, 12, 31)
			else:
				from datetime import timedelta
				q_end = date(year, quarter * 3 + 1, 1) - timedelta(days=1)
			periods.append((period_key, q_start, q_end))
			# Next quarter
			if quarter == 4:
				current = date(year + 1, 1, 1)
			else:
				current = date(year, quarter * 3 + 1, 1)

	elif group_by == "Year":
		while current <= to_date:
			year = current.year
			period_key = str(year)
			periods.append((period_key, date(year, 1, 1), date(year, 12, 31)))
			current = date(year + 1, 1, 1)

	else:
		# Default to Month
		return generate_periods(from_date, to_date, "Month")

	return periods


def get_chart_data(data, filters):
	if not data:
		return None

	labels = [d["period"] for d in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": "Lease Revenue", "values": [d["lease_revenue"] for d in data]},
				{"name": "Rental Revenue", "values": [d["rental_revenue"] for d in data]},
				{"name": "Net Revenue", "values": [d["net_revenue"] for d in data]},
			]
		},
		"type": "line",
		"colors": ["#4C9AFF", "#28a745", "#ffc107"],
		"height": 300
	}
