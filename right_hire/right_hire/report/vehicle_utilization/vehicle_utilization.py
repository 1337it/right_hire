# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, date_diff, flt, today
from datetime import date, timedelta


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"fieldname": "vehicle", "label": _("Vehicle"), "fieldtype": "Link", "options": "Vehicle", "width": 160},
		{"fieldname": "plate_no", "label": _("Plate No"), "fieldtype": "Data", "width": 100},
		{"fieldname": "make_model", "label": _("Make/Model"), "fieldtype": "Data", "width": 150},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 90},
		{"fieldname": "total_days", "label": _("Period Days"), "fieldtype": "Int", "width": 90},
		{"fieldname": "leased_days", "label": _("Leased Days"), "fieldtype": "Int", "width": 90},
		{"fieldname": "rented_days", "label": _("Rented Days"), "fieldtype": "Int", "width": 90},
		{"fieldname": "utilized_days", "label": _("Utilized Days"), "fieldtype": "Int", "width": 100},
		{"fieldname": "utilization_pct", "label": _("Utilization %"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "lease_revenue", "label": _("Lease Revenue"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "rental_revenue", "label": _("Rental Revenue"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_revenue", "label": _("Total Revenue"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "expenses", "label": _("Expenses"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "salik_cost", "label": _("Salik"), "fieldtype": "Currency", "width": 90},
		{"fieldname": "net_revenue", "label": _("Net Revenue"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else getdate(today()).replace(day=1)
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else getdate(today())
	total_days = date_diff(to_date, from_date) + 1

	if total_days <= 0:
		return []

	# Get all vehicles
	vehicle_filters = {"docstatus": ["<", 2]}
	if filters.get("vehicle"):
		vehicle_filters["name"] = filters.get("vehicle")

	vehicles = frappe.db.get_all("Vehicle",
		filters=vehicle_filters,
		fields=["name", "plate_no", "make", "model", "year", "status", "vehicle_type"]
	)

	if not vehicles:
		return []

	vehicle_names = [v.name for v in vehicles]

	# Get lease agreements overlapping with date range
	leases = frappe.db.sql("""
		SELECT vehicle, start_date, end_date, monthly_rate, grand_total, tenure_months
		FROM `tabLease Agreement`
		WHERE docstatus = 1
		AND vehicle IN %(vehicles)s
		AND start_date <= %(to_date)s
		AND end_date >= %(from_date)s
	""", {"vehicles": vehicle_names, "from_date": from_date, "to_date": to_date}, as_dict=1)

	# Get rental agreements overlapping with date range
	rentals = frappe.db.sql("""
		SELECT vehicle, start_datetime, end_datetime, grand_total, planned_days
		FROM `tabRental Agreement`
		WHERE docstatus = 1
		AND vehicle IN %(vehicles)s
		AND DATE(start_datetime) <= %(to_date)s
		AND DATE(IFNULL(end_datetime, start_datetime)) >= %(from_date)s
	""", {"vehicles": vehicle_names, "from_date": from_date, "to_date": to_date}, as_dict=1)

	# Get vehicle expenses in date range
	expenses = frappe.db.sql("""
		SELECT vehicle, SUM(total_amount) as total
		FROM `tabVehicle Expense`
		WHERE docstatus < 2
		AND vehicle IN %(vehicles)s
		AND expense_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY vehicle
	""", {"vehicles": vehicle_names, "from_date": from_date, "to_date": to_date}, as_dict=1)
	expense_map = {e.vehicle: flt(e.total) for e in expenses}

	# Get salik charges in date range
	salik = frappe.db.sql("""
		SELECT vehicle, SUM(toll_amount) as total
		FROM `tabSalik Transaction`
		WHERE vehicle IN %(vehicles)s
		AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY vehicle
	""", {"vehicles": vehicle_names, "from_date": from_date, "to_date": to_date}, as_dict=1)
	salik_map = {s.vehicle: flt(s.total) for s in salik}

	# Build lease days and revenue per vehicle
	lease_data = {}  # {vehicle: {"days": X, "revenue": Y}}
	for l in leases:
		overlap_start = max(getdate(l.start_date), from_date)
		overlap_end = min(getdate(l.end_date), to_date)
		days = date_diff(overlap_end, overlap_start) + 1
		if days <= 0:
			continue

		daily_rate = flt(l.monthly_rate) / 30.0 if l.monthly_rate else 0
		revenue = daily_rate * days

		if l.vehicle not in lease_data:
			lease_data[l.vehicle] = {"days": 0, "revenue": 0}
		lease_data[l.vehicle]["days"] += days
		lease_data[l.vehicle]["revenue"] += revenue

	# Build rental days and revenue per vehicle
	rental_data = {}
	for r in rentals:
		r_start = getdate(r.start_datetime)
		r_end = getdate(r.end_datetime) if r.end_datetime else r_start
		overlap_start = max(r_start, from_date)
		overlap_end = min(r_end, to_date)
		days = date_diff(overlap_end, overlap_start) + 1
		if days <= 0:
			continue

		total_rental_days = date_diff(r_end, r_start) + 1
		if total_rental_days > 0:
			revenue = flt(r.grand_total) * days / total_rental_days
		else:
			revenue = flt(r.grand_total)

		if r.vehicle not in rental_data:
			rental_data[r.vehicle] = {"days": 0, "revenue": 0}
		rental_data[r.vehicle]["days"] += days
		rental_data[r.vehicle]["revenue"] += revenue

	# Build report data
	data = []
	for v in vehicles:
		ld = lease_data.get(v.name, {"days": 0, "revenue": 0})
		rd = rental_data.get(v.name, {"days": 0, "revenue": 0})
		utilized_days = min(ld["days"] + rd["days"], total_days)
		lease_revenue = flt(ld["revenue"], 2)
		rental_revenue = flt(rd["revenue"], 2)
		total_revenue = lease_revenue + rental_revenue
		exp = expense_map.get(v.name, 0)
		salik_cost = salik_map.get(v.name, 0)
		net = total_revenue - exp - salik_cost
		util_pct = (utilized_days / total_days * 100) if total_days > 0 else 0

		make_model = " ".join(filter(None, [v.make, v.model, str(v.year or "")]))

		data.append({
			"vehicle": v.name,
			"plate_no": v.plate_no,
			"make_model": make_model,
			"status": v.status,
			"total_days": total_days,
			"leased_days": ld["days"],
			"rented_days": rd["days"],
			"utilized_days": utilized_days,
			"utilization_pct": flt(util_pct, 1),
			"lease_revenue": lease_revenue,
			"rental_revenue": rental_revenue,
			"total_revenue": total_revenue,
			"expenses": exp,
			"salik_cost": salik_cost,
			"net_revenue": flt(net, 2),
		})

	data.sort(key=lambda x: x["utilization_pct"], reverse=True)
	return data


def get_chart(data):
	if not data:
		return None

	labels = [d["plate_no"] or d["vehicle"] for d in data[:10]]
	utilization = [d["utilization_pct"] for d in data[:10]]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": "Utilization %", "values": utilization}]
		},
		"type": "bar",
		"colors": ["#4C9AFF"],
		"barOptions": {"stacked": False}
	}
