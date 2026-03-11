# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, date_diff


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
		{"fieldname": "purchase_cost", "label": _("Purchase Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "current_book_value", "label": _("Current Book Value"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "lease_revenue", "label": _("Lease Revenue"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "rental_revenue", "label": _("Rental Revenue"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_revenue", "label": _("Total Revenue"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_expenses", "label": _("Total Expenses"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "salik_cost", "label": _("Salik Charges"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "fines_cost", "label": _("Fines (Unpaid)"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "net_profit", "label": _("Net Profit"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "roi", "label": _("ROI %"), "fieldtype": "Percent", "width": 90},
		{"fieldname": "monthly_avg", "label": _("Avg Monthly Profit"), "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	# Get vehicles
	vehicle_filters = {"docstatus": ["<", 2]}
	if filters and filters.get("vehicle"):
		vehicle_filters["name"] = filters.get("vehicle")

	vehicles = frappe.db.get_all("Vehicle",
		filters=vehicle_filters,
		fields=["name", "plate_no", "make", "model", "year", "status", "purchase_cost", "purchase_date", "current_book_value"]
	)

	if not vehicles:
		return []

	vehicle_names = [v.name for v in vehicles]

	# Calculate lease revenue per vehicle (from monthly_rate * months active)
	lease_revenue = frappe.db.sql("""
		SELECT vehicle,
			SUM(
				monthly_rate * GREATEST(1,
					TIMESTAMPDIFF(MONTH, start_date,
						LEAST(end_date, CURDATE())
					)
				)
			) as revenue
		FROM `tabLease Agreement`
		WHERE docstatus = 1
		AND vehicle IN %(vehicles)s
		AND lease_status IN ('Active', 'Terminated')
		AND start_date <= CURDATE()
		GROUP BY vehicle
	""", {"vehicles": vehicle_names}, as_dict=1)
	lease_rev_map = {r.vehicle: flt(r.revenue) for r in lease_revenue}

	# Calculate rental revenue per vehicle
	rental_revenue = frappe.db.sql("""
		SELECT vehicle, SUM(grand_total) as revenue
		FROM `tabRental Agreement`
		WHERE docstatus = 1
		AND vehicle IN %(vehicles)s
		GROUP BY vehicle
	""", {"vehicles": vehicle_names}, as_dict=1)
	rental_rev_map = {r.vehicle: flt(r.revenue) for r in rental_revenue}

	# Calculate total expenses per vehicle
	expenses = frappe.db.sql("""
		SELECT vehicle, SUM(total_amount) as total
		FROM `tabVehicle Expense`
		WHERE docstatus < 2
		AND vehicle IN %(vehicles)s
		GROUP BY vehicle
	""", {"vehicles": vehicle_names}, as_dict=1)
	expense_map = {e.vehicle: flt(e.total) for e in expenses}

	# Calculate total salik per vehicle
	salik = frappe.db.sql("""
		SELECT vehicle, SUM(toll_amount) as total
		FROM `tabSalik Transaction`
		WHERE vehicle IN %(vehicles)s
		GROUP BY vehicle
	""", {"vehicles": vehicle_names}, as_dict=1)
	salik_map = {s.vehicle: flt(s.total) for s in salik}

	# Calculate unpaid fines per vehicle
	fines = frappe.db.sql("""
		SELECT vehicle, SUM(amount) as total
		FROM `tabTraffic Fine`
		WHERE vehicle IN %(vehicles)s
		AND paid = 0
		GROUP BY vehicle
	""", {"vehicles": vehicle_names}, as_dict=1)
	fines_map = {f.vehicle: flt(f.total) for f in fines}

	data = []
	for v in vehicles:
		purchase_cost = flt(v.purchase_cost)
		l_rev = lease_rev_map.get(v.name, 0)
		r_rev = rental_rev_map.get(v.name, 0)
		total_rev = l_rev + r_rev
		exp = expense_map.get(v.name, 0)
		salik_cost = salik_map.get(v.name, 0)
		fines_cost = fines_map.get(v.name, 0)
		net = total_rev - exp - salik_cost - fines_cost

		roi = (net / purchase_cost * 100) if purchase_cost > 0 else 0

		# Calculate months since purchase for avg monthly profit
		months_active = 1
		if v.purchase_date:
			months_active = max(1, date_diff(today(), v.purchase_date) // 30)
		monthly_avg = net / months_active

		make_model = " ".join(filter(None, [v.make, v.model, str(v.year or "")]))

		data.append({
			"vehicle": v.name,
			"plate_no": v.plate_no,
			"make_model": make_model,
			"status": v.status,
			"purchase_cost": purchase_cost,
			"current_book_value": flt(v.current_book_value),
			"lease_revenue": l_rev,
			"rental_revenue": r_rev,
			"total_revenue": total_rev,
			"total_expenses": exp,
			"salik_cost": salik_cost,
			"fines_cost": fines_cost,
			"net_profit": flt(net, 2),
			"roi": flt(roi, 1),
			"monthly_avg": flt(monthly_avg, 2),
		})

	data.sort(key=lambda x: x["net_profit"], reverse=True)
	return data


def get_chart(data):
	if not data:
		return None

	labels = [d["plate_no"] or d["vehicle"] for d in data[:10]]
	revenue = [d["total_revenue"] for d in data[:10]]
	expenses = [d["total_expenses"] + d["salik_cost"] + d["fines_cost"] for d in data[:10]]
	profit = [d["net_profit"] for d in data[:10]]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": "Revenue", "values": revenue},
				{"name": "Costs", "values": expenses},
				{"name": "Net Profit", "values": profit}
			]
		},
		"type": "bar",
		"colors": ["#28a745", "#dc3545", "#4C9AFF"],
		"barOptions": {"stacked": False}
	}
