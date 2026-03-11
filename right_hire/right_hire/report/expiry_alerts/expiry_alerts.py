# Copyright (c) 2026, Right Hire and contributors
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
		{"fieldname": "vehicle", "label": _("Vehicle"), "fieldtype": "Link", "options": "Vehicle", "width": 160},
		{"fieldname": "plate_no", "label": _("Plate No"), "fieldtype": "Data", "width": 100},
		{"fieldname": "make_model", "label": _("Make/Model"), "fieldtype": "Data", "width": 150},
		{"fieldname": "expiry_type", "label": _("Expiry Type"), "fieldtype": "Data", "width": 120},
		{"fieldname": "expiry_date", "label": _("Expiry Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "days_remaining", "label": _("Days Remaining"), "fieldtype": "Int", "width": 100},
		{"fieldname": "urgency", "label": _("Urgency"), "fieldtype": "Data", "width": 100},
		{"fieldname": "status", "label": _("Vehicle Status"), "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	data = []

	vehicles = frappe.db.get_all("Vehicle",
		filters={"docstatus": ["<", 2]},
		fields=["name as vehicle", "plate_no", "make", "model", "year",
				"registration_expiry", "insurance_expiry", "next_service_due", "status"]
	)

	today_date = getdate(today())

	for v in vehicles:
		make_model = " ".join(filter(None, [v.make, v.model, str(v.year or "")]))

		# Check registration expiry
		if v.registration_expiry:
			days = date_diff(v.registration_expiry, today_date)
			if days <= 90:
				data.append({
					"vehicle": v.vehicle,
					"plate_no": v.plate_no,
					"make_model": make_model,
					"expiry_type": "Registration",
					"expiry_date": v.registration_expiry,
					"days_remaining": days,
					"urgency": get_urgency(days),
					"status": v.status,
				})

		# Check insurance expiry
		if v.insurance_expiry:
			days = date_diff(v.insurance_expiry, today_date)
			if days <= 90:
				data.append({
					"vehicle": v.vehicle,
					"plate_no": v.plate_no,
					"make_model": make_model,
					"expiry_type": "Insurance",
					"expiry_date": v.insurance_expiry,
					"days_remaining": days,
					"urgency": get_urgency(days),
					"status": v.status,
				})

		# Check service due
		if v.next_service_due:
			days = date_diff(v.next_service_due, today_date)
			if days <= 30:
				data.append({
					"vehicle": v.vehicle,
					"plate_no": v.plate_no,
					"make_model": make_model,
					"expiry_type": "Service Due",
					"expiry_date": v.next_service_due,
					"days_remaining": days,
					"urgency": get_urgency(days),
					"status": v.status,
				})

	# Sort by urgency (overdue first, then by days remaining)
	data.sort(key=lambda x: (x["urgency"] != "Overdue", x["days_remaining"]))

	return data


def get_urgency(days_remaining):
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
