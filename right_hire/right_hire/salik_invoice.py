"""
Salik Invoice Helper
Generate Sales Invoice items from Salik Transactions with markup
"""

import frappe
from frappe import _
from collections import defaultdict


# Salik markup percentage
SALIK_MARKUP_PERCENT = 10


def get_salik_rates():
	"""Get Salik toll rates by schedule"""
	return {
		"Peak": 6.0,      # AED 6 for Peak (weekday)
		"Low-Peak": 4.0,  # AED 4 for Low-Peak
		"Off-Peak": 0.0   # AED 0 for Off-Peak (free)
	}


def get_rate_with_markup(base_rate, markup_percent=SALIK_MARKUP_PERCENT):
	"""Calculate rate with markup"""
	return base_rate * (1 + markup_percent / 100)


@frappe.whitelist()
def get_salik_invoice_items(vehicle=None, lease_agreement=None, rental_agreement=None, from_date=None, to_date=None):
	"""
	Get Salik transactions grouped by schedule for invoice line items.

	Args:
		vehicle: Vehicle name (optional)
		lease_agreement: Lease Agreement name (optional)
		rental_agreement: Rental Agreement name (optional)
		from_date: Start date filter (optional)
		to_date: End date filter (optional)

	Returns:
		list: Invoice items grouped by toll schedule with markup applied
	"""
	filters = {
		"charged_to_customer": 0,  # Not yet charged
		"docstatus": ["<", 2]      # Not cancelled
	}

	if vehicle:
		filters["vehicle"] = vehicle
	if lease_agreement:
		filters["lease_agreement"] = lease_agreement
	if rental_agreement:
		filters["linked_agreement"] = rental_agreement
	if from_date:
		filters["transaction_date"] = [">=", from_date]
	if to_date:
		if "transaction_date" in filters:
			filters["transaction_date"] = ["between", [from_date, to_date]]
		else:
			filters["transaction_date"] = ["<=", to_date]

	# Get all matching Salik transactions
	transactions = frappe.get_all(
		"Salik Transaction",
		filters=filters,
		fields=["name", "toll_schedule", "toll_amount", "transaction_date", "gate_location", "vehicle"]
	)

	if not transactions:
		return []

	# Group by toll schedule
	grouped = defaultdict(lambda: {"count": 0, "total_amount": 0, "transactions": []})

	for trans in transactions:
		schedule = trans.toll_schedule or "Peak"
		grouped[schedule]["count"] += 1
		grouped[schedule]["total_amount"] += float(trans.toll_amount or 0)
		grouped[schedule]["transactions"].append(trans.name)

	# Get Salik rates
	salik_rates = get_salik_rates()

	# Create invoice items
	items = []
	for schedule, data in grouped.items():
		if data["count"] == 0:
			continue

		base_rate = salik_rates.get(schedule, 4.00)

		# Skip Off-Peak (free)
		if base_rate == 0:
			continue

		rate_with_markup = get_rate_with_markup(base_rate)

		item = {
			"item_name": f"Salik Toll - {schedule}",
			"description": f"Salik Toll Charges ({schedule} Hours)\n{data['count']} trip(s)",
			"qty": data["count"],
			"rate": rate_with_markup,
			"amount": rate_with_markup * data["count"],
			"uom": "Nos",
			"toll_schedule": schedule,
			"base_toll_rate": base_rate,
			"markup_percent": SALIK_MARKUP_PERCENT,
			"salik_transactions": data["transactions"],
			"total_base_amount": data["total_amount"]
		}
		items.append(item)

	# Sort by schedule: Peak first, then Low-Peak, then Off-Peak
	schedule_order = {"Peak": 0, "Low-Peak": 1, "Off-Peak": 2}
	items.sort(key=lambda x: schedule_order.get(x["toll_schedule"], 99))

	return items


@frappe.whitelist()
def add_salik_items_to_invoice(sales_invoice, vehicle=None, lease_agreement=None, rental_agreement=None):
	"""
	Add Salik transaction items to a Sales Invoice.

	Args:
		sales_invoice: Sales Invoice name
		vehicle: Vehicle name (optional)
		lease_agreement: Lease Agreement name (optional)
		rental_agreement: Rental Agreement name (optional)

	Returns:
		dict: Result with added items count
	"""
	doc = frappe.get_doc("Sales Invoice", sales_invoice)

	if doc.docstatus != 0:
		frappe.throw(_("Cannot modify submitted invoice"))

	# Get vehicle from invoice custom fields if not provided
	if not vehicle and hasattr(doc, 'vehicle') and doc.vehicle:
		vehicle = doc.vehicle
	if not lease_agreement and hasattr(doc, 'lease_agreement') and doc.lease_agreement:
		lease_agreement = doc.lease_agreement
	if not rental_agreement and hasattr(doc, 'rental_agreement') and doc.rental_agreement:
		rental_agreement = doc.rental_agreement

	# Get Salik items
	salik_items = get_salik_invoice_items(
		vehicle=vehicle,
		lease_agreement=lease_agreement,
		rental_agreement=rental_agreement
	)

	if not salik_items:
		frappe.msgprint(_("No pending Salik transactions found"))
		return {"added": 0}

	# Get or create Salik service item
	salik_item_code = get_or_create_salik_item()

	added_count = 0
	all_transactions = []

	for item_data in salik_items:
		# Skip if zero amount
		if item_data["amount"] == 0:
			continue

		doc.append("items", {
			"item_code": salik_item_code,
			"item_name": item_data["item_name"],
			"description": item_data["description"],
			"qty": item_data["qty"],
			"rate": item_data["rate"],
			"amount": item_data["amount"],
			"uom": "Nos"
		})
		added_count += 1
		all_transactions.extend(item_data["salik_transactions"])

	if added_count > 0:
		doc.save()

		# Mark transactions as charged
		for trans_name in all_transactions:
			frappe.db.set_value("Salik Transaction", trans_name, {
				"charged_to_customer": 1,
				"invoice_reference": sales_invoice,
				"customer_charged_date": frappe.utils.nowdate()
			}, update_modified=False)

		frappe.db.commit()

	return {
		"added": added_count,
		"transactions_linked": len(all_transactions),
		"items": salik_items
	}


def get_or_create_salik_item():
	"""Get or create a Salik service item"""
	item_code = "SALIK-TOLL"

	if not frappe.db.exists("Item", item_code):
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = "Salik Toll Charges"
		item.item_group = "Services"
		item.stock_uom = "Nos"
		item.is_stock_item = 0
		item.is_sales_item = 1
		item.include_item_in_manufacturing = 0
		item.description = "Salik Toll Gate Charges"
		item.flags.ignore_mandatory = True
		item.insert(ignore_permissions=True)
		frappe.db.commit()

	return item_code


@frappe.whitelist()
def get_salik_summary(vehicle=None, lease_agreement=None, rental_agreement=None):
	"""
	Get a summary of pending Salik charges for display.

	Returns:
		dict: Summary with counts and amounts by schedule
	"""
	items = get_salik_invoice_items(
		vehicle=vehicle,
		lease_agreement=lease_agreement,
		rental_agreement=rental_agreement
	)

	summary = {
		"total_trips": 0,
		"total_base_amount": 0,
		"total_with_markup": 0,
		"markup_percent": SALIK_MARKUP_PERCENT,
		"by_schedule": []
	}

	for item in items:
		summary["total_trips"] += item["qty"]
		summary["total_base_amount"] += item["total_base_amount"]
		summary["total_with_markup"] += item["amount"]
		summary["by_schedule"].append({
			"schedule": item["toll_schedule"],
			"trips": item["qty"],
			"base_rate": item["base_toll_rate"],
			"rate_with_markup": item["rate"],
			"amount": item["amount"]
		})

	return summary
