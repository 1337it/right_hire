# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today, getdate, date_diff


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"fieldname": "vehicle", "label": _("Vehicle"), "fieldtype": "Link", "options": "Vehicle", "width": 160},
		{"fieldname": "plate_no", "label": _("Plate No"), "fieldtype": "Data", "width": 100},
		{"fieldname": "make_model", "label": _("Make/Model"), "fieldtype": "Data", "width": 150},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "current_agreement", "label": _("Current Agreement"), "fieldtype": "Data", "width": 150},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Data", "width": 150},
		{"fieldname": "agreement_end", "label": _("Agreement End"), "fieldtype": "Date", "width": 110},
		{"fieldname": "odometer", "label": _("Odometer (KM)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "registration_expiry", "label": _("Reg. Expiry"), "fieldtype": "Date", "width": 100},
		{"fieldname": "reg_days_left", "label": _("Reg. Days Left"), "fieldtype": "Int", "width": 100},
		{"fieldname": "insurance_expiry", "label": _("Ins. Expiry"), "fieldtype": "Date", "width": 100},
		{"fieldname": "ins_days_left", "label": _("Ins. Days Left"), "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters and filters.get("status"):
		conditions.append("v.status = %(status)s")
		values["status"] = filters.get("status")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	vehicles = frappe.db.sql("""
		SELECT
			v.name as vehicle,
			v.plate_no,
			v.make, v.model, v.year,
			v.status,
			v.current_agreement_type,
			v.current_agreement,
			v.odometer,
			v.registration_expiry,
			v.insurance_expiry
		FROM `tabVehicle` v
		WHERE {where_clause}
		ORDER BY v.status, v.plate_no
	""".format(where_clause=where_clause), values, as_dict=1)

	today_date = getdate(today())
	data = []

	for v in vehicles:
		make_model = " ".join(filter(None, [v.make, v.model, str(v.year or "")]))

		# Get current agreement details
		customer = ""
		agreement_end = None
		if v.current_agreement:
			if v.current_agreement_type == "Lease":
				la = frappe.db.get_value("Lease Agreement", v.current_agreement,
					["customer_name", "end_date"], as_dict=True)
				if la:
					customer = la.customer_name or ""
					agreement_end = la.end_date
			elif v.current_agreement_type == "Rental":
				ra = frappe.db.get_value("Rental Agreement", v.current_agreement,
					["customer_name", "end_datetime"], as_dict=True)
				if ra:
					customer = ra.customer_name or ""
					agreement_end = getdate(ra.end_datetime) if ra.end_datetime else None

		reg_days = date_diff(v.registration_expiry, today_date) if v.registration_expiry else None
		ins_days = date_diff(v.insurance_expiry, today_date) if v.insurance_expiry else None

		data.append({
			"vehicle": v.vehicle,
			"plate_no": v.plate_no,
			"make_model": make_model,
			"status": v.status,
			"current_agreement": v.current_agreement or "-",
			"customer": customer or "-",
			"agreement_end": agreement_end,
			"odometer": v.odometer or 0,
			"registration_expiry": v.registration_expiry,
			"reg_days_left": reg_days,
			"insurance_expiry": v.insurance_expiry,
			"ins_days_left": ins_days,
		})

	return data


def get_chart_data(data):
	if not data:
		return None

	status_count = {}
	for row in data:
		status = row["status"] or "Unknown"
		status_count[status] = status_count.get(status, 0) + 1

	return {
		"data": {
			"labels": list(status_count.keys()),
			"datasets": [{"name": "Vehicles", "values": list(status_count.values())}]
		},
		"type": "donut",
		"height": 300,
		"colors": ["#28a745", "#ffc107", "#17a2b8", "#dc3545", "#6c757d"]
	}
