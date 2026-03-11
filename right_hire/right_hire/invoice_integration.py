"""
Invoice Integration for Salik and Traffic Fines
Automatically adds unpaid charges to customer invoices
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

@frappe.whitelist()
def get_pending_charges(contract=None, agreement=None, vehicle=None):
	"""
	Get all pending (unpaid/uncharged) Salik and RTA charges
	for a specific contract, agreement, or vehicle
	"""
	charges = {
		"salik_transactions": [],
		"traffic_fines": [],
		"total_amount": 0
	}

	# Get Salik transactions
	salik_filters = {
		"charged_to_customer": 0,
		"status": ["!=", "Waived"]
	}

	if contract:
		salik_filters["linked_contract"] = contract
	elif agreement:
		salik_filters["linked_agreement"] = agreement
	elif vehicle:
		salik_filters["vehicle"] = vehicle

	salik_transactions = frappe.get_all(
		"Salik Transaction",
		filters=salik_filters,
		fields=["name", "vehicle", "transaction_date", "gate_location",
		        "toll_amount", "linked_contract", "linked_agreement"],
		order_by="transaction_date asc"
	)

	for trans in salik_transactions:
		charges["salik_transactions"].append(trans)
		charges["total_amount"] += flt(trans.toll_amount)

	# Get Traffic Fines
	fine_filters = {
		"charged_to_customer": 0
	}

	if contract:
		fine_filters["linked_contract"] = contract
	elif agreement:
		fine_filters["linked_agreement"] = agreement
	elif vehicle:
		fine_filters["vehicle"] = vehicle

	traffic_fines = frappe.get_all(
		"Traffic Fine",
		filters=fine_filters,
		fields=["name", "vehicle", "fine_date", "fine_number", "location",
		        "amount", "black_points", "linked_contract", "linked_agreement"],
		order_by="fine_date asc"
	)

	for fine in traffic_fines:
		charges["traffic_fines"].append(fine)
		charges["total_amount"] += flt(fine.amount)

	return charges


def add_charges_to_invoice(invoice_doc, method=None):
	"""
	Hook to automatically add pending charges to invoice
	Triggered on before_insert of Invoice
	"""
	# Only process if invoice is linked to a contract or agreement via reference fields
	contract = None
	agreement = None

	if invoice_doc.reference_type == "Lease Contract" and invoice_doc.reference_name:
		contract = invoice_doc.reference_name
	elif invoice_doc.reference_type == "Rental Agreement" and invoice_doc.reference_name:
		agreement = invoice_doc.reference_name
	else:
		return

	# Get pending charges
	charges = get_pending_charges(contract=contract, agreement=agreement)

	if not charges["salik_transactions"] and not charges["traffic_fines"]:
		return

	# Add Salik charges as line items
	for salik in charges["salik_transactions"]:
		invoice_doc.append("items", {
			"item_name": "Salik Toll Charge",
			"description": f"Salik - {salik.gate_location} on {salik.transaction_date}",
			"qty": 1,
			"rate": salik.toll_amount,
			"amount": salik.toll_amount
		})

	# Add Traffic Fines as line items
	for fine in charges["traffic_fines"]:
		description = f"Traffic Fine #{fine.fine_number} - {fine.fine_date}"
		if fine.location:
			description += f"\nLocation: {fine.location}"
		if fine.black_points:
			description += f"\nBlack Points: {fine.black_points}"

		invoice_doc.append("items", {
			"item_name": "Traffic Fine",
			"description": description,
			"qty": 1,
			"rate": fine.amount,
			"amount": fine.amount
		})


def mark_charges_as_billed(invoice_doc, method=None):
	"""
	Hook to mark charges as billed after invoice is submitted
	Triggered on on_submit of Invoice
	"""
	# Mark all pending charges for the contract/agreement as billed
	contract = None
	agreement = None

	if invoice_doc.reference_type == "Lease Contract" and invoice_doc.reference_name:
		contract = invoice_doc.reference_name
	elif invoice_doc.reference_type == "Rental Agreement" and invoice_doc.reference_name:
		agreement = invoice_doc.reference_name

	if contract or agreement:
		# Mark Salik transactions
		salik_filters = {"charged_to_customer": 0}
		if contract:
			salik_filters["linked_contract"] = contract
		else:
			salik_filters["linked_agreement"] = agreement

		salik_transactions = frappe.get_all("Salik Transaction", filters=salik_filters)
		for trans in salik_transactions:
			salik_doc = frappe.get_doc("Salik Transaction", trans.name)
			salik_doc.charged_to_customer = 1
			salik_doc.customer_charge_amount = salik_doc.toll_amount
			salik_doc.customer_charged_date = nowdate()
			salik_doc.invoice_reference = invoice_doc.name
			salik_doc.save(ignore_permissions=True)

		# Mark Traffic Fines
		fine_filters = {"charged_to_customer": 0}
		if contract:
			fine_filters["linked_contract"] = contract
		else:
			fine_filters["linked_agreement"] = agreement

		traffic_fines = frappe.get_all("Traffic Fine", filters=fine_filters)
		for fine in traffic_fines:
			fine_doc = frappe.get_doc("Traffic Fine", fine.name)
			fine_doc.charged_to_customer = 1
			fine_doc.customer_charge_amount = fine_doc.amount
			fine_doc.customer_charged_date = nowdate()
			fine_doc.invoice_reference = invoice_doc.name
			fine_doc.save(ignore_permissions=True)

		frappe.db.commit()


def get_salik_item_code():
	"""Get or create Salik item code"""
	item_code = "SALIK-CHARGE"

	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": "Salik Toll Charge",
			"item_group": "Services",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
			"description": "Salik toll road charges passed to customer"
		})
		item.insert(ignore_permissions=True)
		frappe.db.commit()

	return item_code


def get_traffic_fine_item_code():
	"""Get or create Traffic Fine item code"""
	item_code = "RTA-FINE"

	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": "Traffic Fine",
			"item_group": "Services",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
			"description": "RTA traffic fines passed to customer"
		})
		item.insert(ignore_permissions=True)
		frappe.db.commit()

	return item_code


@frappe.whitelist()
def add_pending_charges_to_existing_invoice(invoice_name):
	"""
	Manually add pending charges to an existing draft invoice
	"""
	invoice_doc = frappe.get_doc("Invoice", invoice_name)

	if invoice_doc.status not in ["Draft", "Unpaid"]:
		frappe.throw(_("Can only add charges to draft or unpaid invoices"))

	# Get contract/agreement from reference fields
	contract = None
	agreement = None

	if invoice_doc.reference_type == "Lease Contract":
		contract = invoice_doc.reference_name
	elif invoice_doc.reference_type == "Rental Agreement":
		agreement = invoice_doc.reference_name

	if not contract and not agreement:
		frappe.throw(_("Invoice must be linked to a contract or agreement"))

	# Add charges
	add_charges_to_invoice(invoice_doc)
	invoice_doc.save(ignore_permissions=True)

	frappe.msgprint(_("Pending charges added to invoice"))

	return invoice_doc


@frappe.whitelist()
def create_invoice_with_charges(contract=None, agreement=None, customer=None):
	"""
	Create a new invoice with pending charges for a contract/agreement
	"""
	if not customer:
		if contract:
			contract_doc = frappe.get_doc("Lease Contract", contract)
			customer = contract_doc.customer
		elif agreement:
			agreement_doc = frappe.get_doc("Rental Agreement", agreement)
			customer = agreement_doc.customer
		else:
			frappe.throw(_("Customer is required"))

	# Get pending charges
	charges = get_pending_charges(contract=contract, agreement=agreement)

	if not charges["salik_transactions"] and not charges["traffic_fines"]:
		frappe.msgprint(_("No pending charges found"))
		return None

	# Create invoice
	invoice = frappe.new_doc("Invoice")
	invoice.customer = customer
	invoice.posting_date = nowdate()
	invoice.due_date = frappe.utils.add_days(nowdate(), 7)  # 7 days payment term
	invoice.status = "Draft"

	# Link to contract/agreement via reference fields
	if contract:
		invoice.reference_type = "Lease Contract"
		invoice.reference_name = contract
	elif agreement:
		invoice.reference_type = "Rental Agreement"
		invoice.reference_name = agreement

	# Add charges
	add_charges_to_invoice(invoice)

	# Calculate totals
	invoice.total = sum([item.amount for item in invoice.items])
	invoice.tax_amount = 0  # Add tax calculation if needed
	invoice.grand_total = invoice.total + invoice.tax_amount
	invoice.outstanding = invoice.grand_total
	invoice.paid_amount = 0

	invoice.insert(ignore_permissions=True)

	frappe.msgprint(_("Invoice {0} created with {1} charges totaling {2} AED").format(
		invoice.name,
		len(charges["salik_transactions"]) + len(charges["traffic_fines"]),
		invoice.grand_total
	))

	return invoice.name
