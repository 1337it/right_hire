# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, date_diff, cstr


def execute(filters=None):
	if not filters:
		filters = {}

	ageing_as_on = getdate(filters.get("ageing_as_on") or today())
	ranges = parse_ageing_range(filters.get("ageing_range") or "30,60,90,120")

	columns = get_columns(ranges)
	data, totals = get_data(filters, ageing_as_on, ranges)
	chart = get_chart(data, ranges)

	return columns, data, None, chart


def parse_ageing_range(range_str):
	"""Parse '30,60,90,120' into [(0,30), (31,60), (61,90), (91,120), (121, None)]"""
	days = [int(d.strip()) for d in range_str.split(",") if d.strip()]
	ranges = []
	prev = 0
	for d in sorted(days):
		ranges.append((prev, d))
		prev = d + 1
	ranges.append((prev, None))  # 121+ bucket
	return ranges


def get_columns(ranges):
	cols = [
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 160},
		{"fieldname": "customer_name", "label": _("Customer Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "invoice", "label": _("Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
		{"fieldname": "posting_date", "label": _("Invoice Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "invoiced_amount", "label": _("Invoiced Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "paid_amount", "label": _("Paid Amount"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "outstanding", "label": _("Outstanding"), "fieldtype": "Currency", "width": 120},
	]

	for i, (start, end) in enumerate(ranges):
		if end is None:
			label = f"{start}+"
		else:
			label = f"{start}-{end}"
		cols.append({
			"fieldname": f"range_{i}",
			"label": _(label),
			"fieldtype": "Currency",
			"width": 110,
		})

	cols.append({"fieldname": "days_overdue", "label": _("Days Overdue"), "fieldtype": "Int", "width": 100})
	cols.append({"fieldname": "lease_agreement", "label": _("Lease Agreement"), "fieldtype": "Link", "options": "Lease Agreement", "width": 140})

	return cols


def get_data(filters, ageing_as_on, ranges):
	conditions = ["si.docstatus = 1", "si.outstanding_amount > 0"]
	values = {}

	if filters.get("company"):
		conditions.append("si.company = %(company)s")
		values["company"] = filters["company"]

	if filters.get("customer"):
		conditions.append("si.customer = %(customer)s")
		values["customer"] = filters["customer"]

	# Only invoices posted on or before ageing date
	conditions.append("si.posting_date <= %(ageing_as_on)s")
	values["ageing_as_on"] = ageing_as_on

	where_clause = " AND ".join(conditions)

	invoices = frappe.db.sql(f"""
		SELECT
			si.name as invoice,
			si.customer,
			si.customer_name,
			si.posting_date,
			si.due_date,
			si.grand_total as invoiced_amount,
			si.grand_total - si.outstanding_amount as paid_amount,
			si.outstanding_amount as outstanding
		FROM `tabSales Invoice` si
		WHERE {where_clause}
		ORDER BY si.customer, si.posting_date
	""", values, as_dict=True)

	data = []

	for inv in invoices:
		row = {
			"customer": inv.customer,
			"customer_name": inv.customer_name,
			"invoice": inv.invoice,
			"posting_date": inv.posting_date,
			"due_date": inv.due_date,
			"invoiced_amount": flt(inv.invoiced_amount),
			"paid_amount": flt(inv.paid_amount),
			"outstanding": flt(inv.outstanding),
		}

		# Calculate days overdue from due date
		due = getdate(inv.due_date) if inv.due_date else getdate(inv.posting_date)
		days = date_diff(ageing_as_on, due)
		row["days_overdue"] = max(0, days)

		# Place outstanding into the correct ageing bucket
		for i, (start, end) in enumerate(ranges):
			if end is None:
				row[f"range_{i}"] = flt(inv.outstanding) if days >= start else 0
			else:
				row[f"range_{i}"] = flt(inv.outstanding) if start <= days <= end else 0

		# Try to find linked lease agreement
		lease = frappe.db.sql("""
			SELECT sii.description
			FROM `tabSales Invoice Item` sii
			WHERE sii.parent = %s AND sii.description LIKE '%%Lease Contract%%'
			LIMIT 1
		""", inv.invoice, as_dict=True)

		if lease and lease[0].description:
			import re
			match = re.search(r"(LSE-\d{4}-\d{5})", lease[0].description)
			if match:
				row["lease_agreement"] = match.group(1)

		data.append(row)

	return data, None


def get_chart(data, ranges):
	if not data:
		return None

	# Aggregate totals per bucket
	bucket_totals = [0] * len(ranges)
	for row in data:
		for i in range(len(ranges)):
			bucket_totals[i] += flt(row.get(f"range_{i}", 0))

	labels = []
	for start, end in ranges:
		if end is None:
			labels.append(f"{start}+ days")
		else:
			labels.append(f"{start}-{end} days")

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Outstanding Amount"), "values": bucket_totals}
			]
		},
		"type": "bar",
		"colors": ["#ff5858"],
	}
