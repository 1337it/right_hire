# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, date_diff


def execute(filters=None):
	if not filters:
		filters = {}

	ageing_as_on = getdate(filters.get("ageing_as_on") or today())
	ranges = parse_ageing_range(filters.get("ageing_range") or "30,60,90,120")

	columns = get_columns(ranges)
	data = get_data(filters, ageing_as_on, ranges)
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
	ranges.append((prev, None))
	return ranges


def get_columns(ranges):
	cols = [
		{"fieldname": "supplier", "label": _("Supplier"), "fieldtype": "Link", "options": "Supplier", "width": 160},
		{"fieldname": "supplier_name", "label": _("Supplier Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "invoice", "label": _("Invoice"), "fieldtype": "Link", "options": "Purchase Invoice", "width": 140},
		{"fieldname": "posting_date", "label": _("Invoice Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "invoiced_amount", "label": _("Invoiced Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "paid_amount", "label": _("Paid Amount"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "outstanding", "label": _("Outstanding"), "fieldtype": "Currency", "width": 120},
	]

	for i, (start, end) in enumerate(ranges):
		label = f"{start}+" if end is None else f"{start}-{end}"
		cols.append({
			"fieldname": f"range_{i}",
			"label": _(label),
			"fieldtype": "Currency",
			"width": 110,
		})

	cols.append({"fieldname": "days_overdue", "label": _("Days Overdue"), "fieldtype": "Int", "width": 100})

	return cols


def get_data(filters, ageing_as_on, ranges):
	conditions = ["pi.docstatus = 1", "pi.outstanding_amount > 0"]
	values = {}

	if filters.get("company"):
		conditions.append("pi.company = %(company)s")
		values["company"] = filters["company"]

	if filters.get("supplier"):
		conditions.append("pi.supplier = %(supplier)s")
		values["supplier"] = filters["supplier"]

	conditions.append("pi.posting_date <= %(ageing_as_on)s")
	values["ageing_as_on"] = ageing_as_on

	where_clause = " AND ".join(conditions)

	invoices = frappe.db.sql(f"""
		SELECT
			pi.name as invoice,
			pi.supplier,
			pi.supplier_name,
			pi.posting_date,
			pi.due_date,
			pi.grand_total as invoiced_amount,
			pi.grand_total - pi.outstanding_amount as paid_amount,
			pi.outstanding_amount as outstanding
		FROM `tabPurchase Invoice` pi
		WHERE {where_clause}
		ORDER BY pi.supplier, pi.posting_date
	""", values, as_dict=True)

	data = []

	for inv in invoices:
		row = {
			"supplier": inv.supplier,
			"supplier_name": inv.supplier_name,
			"invoice": inv.invoice,
			"posting_date": inv.posting_date,
			"due_date": inv.due_date,
			"invoiced_amount": flt(inv.invoiced_amount),
			"paid_amount": flt(inv.paid_amount),
			"outstanding": flt(inv.outstanding),
		}

		due = getdate(inv.due_date) if inv.due_date else getdate(inv.posting_date)
		days = date_diff(ageing_as_on, due)
		row["days_overdue"] = max(0, days)

		for i, (start, end) in enumerate(ranges):
			if end is None:
				row[f"range_{i}"] = flt(inv.outstanding) if days >= start else 0
			else:
				row[f"range_{i}"] = flt(inv.outstanding) if start <= days <= end else 0

		data.append(row)

	return data


def get_chart(data, ranges):
	if not data:
		return None

	bucket_totals = [0] * len(ranges)
	for row in data:
		for i in range(len(ranges)):
			bucket_totals[i] += flt(row.get(f"range_{i}", 0))

	labels = []
	for start, end in ranges:
		labels.append(f"{start}+ days" if end is None else f"{start}-{end} days")

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Outstanding Amount"), "values": bucket_totals}
			]
		},
		"type": "bar",
		"colors": ["#f0ad4e"],
	}
