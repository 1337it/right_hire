"""
Payment Tracking for Salik and Traffic Fines
Handles payment recording and reconciliation
"""

import frappe
from frappe import _
from frappe.utils import nowdate, flt

@frappe.whitelist()
def record_salik_payment(transaction_name, paid_amount, payment_date=None, payment_reference=None):
	"""
	Record payment for a Salik transaction
	"""
	salik_doc = frappe.get_doc("Salik Transaction", transaction_name)

	if salik_doc.paid:
		frappe.throw(_("This transaction is already marked as paid"))

	salik_doc.paid = 1
	salik_doc.paid_date = payment_date or nowdate()
	salik_doc.payment_reference = payment_reference
	salik_doc.status = "Paid"
	salik_doc.save(ignore_permissions=True)

	frappe.msgprint(_("Salik transaction {0} marked as paid").format(transaction_name))

	return salik_doc


@frappe.whitelist()
def record_fine_payment(fine_name, paid_amount, payment_date=None, payment_reference=None):
	"""
	Record payment for a traffic fine
	"""
	fine_doc = frappe.get_doc("Traffic Fine", fine_name)

	if fine_doc.paid:
		frappe.throw(_("This fine is already marked as paid"))

	fine_doc.paid = 1
	fine_doc.paid_date = payment_date or nowdate()
	fine_doc.payment_reference = payment_reference
	fine_doc.save(ignore_permissions=True)

	frappe.msgprint(_("Traffic fine {0} marked as paid").format(fine_name))

	return fine_doc


@frappe.whitelist()
def bulk_mark_paid(doctype, names, payment_date=None, payment_reference=None):
	"""
	Mark multiple Salik transactions or fines as paid in bulk
	names should be comma-separated string or list
	"""
	if isinstance(names, str):
		names = [n.strip() for n in names.split(",")]

	paid_count = 0
	errors = []

	for name in names:
		try:
			if doctype == "Salik Transaction":
				record_salik_payment(name, 0, payment_date, payment_reference)
			elif doctype == "Traffic Fine":
				record_fine_payment(name, 0, payment_date, payment_reference)
			paid_count += 1
		except Exception as e:
			errors.append(f"{name}: {str(e)}")

	if errors:
		frappe.msgprint(
			_("Marked {0} records as paid. Errors: {1}").format(paid_count, "; ".join(errors)),
			indicator="orange"
		)
	else:
		frappe.msgprint(_("Successfully marked {0} records as paid").format(paid_count))

	return {"success": paid_count, "errors": errors}


@frappe.whitelist()
def get_payment_summary(vehicle=None, contract=None, agreement=None, from_date=None, to_date=None):
	"""
	Get payment summary for Salik and fines
	"""
	summary = {
		"salik": {
			"total": 0,
			"paid": 0,
			"unpaid": 0,
			"count_paid": 0,
			"count_unpaid": 0
		},
		"fines": {
			"total": 0,
			"paid": 0,
			"unpaid": 0,
			"count_paid": 0,
			"count_unpaid": 0
		},
		"grand_total": 0,
		"grand_paid": 0,
		"grand_unpaid": 0
	}

	# Build filters
	salik_filters = {}
	fine_filters = {}

	if vehicle:
		salik_filters["vehicle"] = vehicle
		fine_filters["vehicle"] = vehicle

	if contract:
		salik_filters["linked_contract"] = contract
		fine_filters["linked_contract"] = contract

	if agreement:
		salik_filters["linked_agreement"] = agreement
		fine_filters["linked_agreement"] = agreement

	if from_date:
		salik_filters["transaction_date"] = [">=", from_date]
		fine_filters["fine_date"] = [">=", from_date]

	if to_date:
		if "transaction_date" in salik_filters:
			salik_filters["transaction_date"] = [[">=", from_date], ["<=", to_date]]
		else:
			salik_filters["transaction_date"] = ["<=", to_date]

		if "fine_date" in fine_filters:
			fine_filters["fine_date"] = [[">=", from_date], ["<=", to_date]]
		else:
			fine_filters["fine_date"] = ["<=", to_date]

	# Get Salik summary
	salik_transactions = frappe.get_all(
		"Salik Transaction",
		filters=salik_filters,
		fields=["name", "toll_amount", "paid"]
	)

	for trans in salik_transactions:
		summary["salik"]["total"] += flt(trans.toll_amount)
		if trans.paid:
			summary["salik"]["paid"] += flt(trans.toll_amount)
			summary["salik"]["count_paid"] += 1
		else:
			summary["salik"]["unpaid"] += flt(trans.toll_amount)
			summary["salik"]["count_unpaid"] += 1

	# Get Fines summary
	fines = frappe.get_all(
		"Traffic Fine",
		filters=fine_filters,
		fields=["name", "amount", "paid"]
	)

	for fine in fines:
		summary["fines"]["total"] += flt(fine.amount)
		if fine.paid:
			summary["fines"]["paid"] += flt(fine.amount)
			summary["fines"]["count_paid"] += 1
		else:
			summary["fines"]["unpaid"] += flt(fine.amount)
			summary["fines"]["count_unpaid"] += 1

	# Calculate grand totals
	summary["grand_total"] = summary["salik"]["total"] + summary["fines"]["total"]
	summary["grand_paid"] = summary["salik"]["paid"] + summary["fines"]["paid"]
	summary["grand_unpaid"] = summary["salik"]["unpaid"] + summary["fines"]["unpaid"]

	return summary


def mark_invoice_charges_paid(invoice_doc, method=None):
	"""
	When an invoice is fully paid, mark related Salik/Fine charges as paid to RTA/Salik
	This is called from a hook on Payment Entry
	"""
	# This would be called when a payment is made against an invoice
	# For now, this is a placeholder for future enhancement
	pass


@frappe.whitelist()
def get_unpaid_charges_report(vehicle=None):
	"""
	Get detailed report of all unpaid charges
	"""
	report = {
		"salik_transactions": [],
		"traffic_fines": [],
		"summary": {}
	}

	# Get unpaid Salik transactions
	salik_filters = {"paid": 0, "status": ["!=", "Waived"]}
	if vehicle:
		salik_filters["vehicle"] = vehicle

	report["salik_transactions"] = frappe.get_all(
		"Salik Transaction",
		filters=salik_filters,
		fields=["name", "vehicle", "transaction_date", "gate_location",
		        "toll_amount", "charged_to_customer", "linked_contract", "linked_agreement"],
		order_by="transaction_date desc"
	)

	# Get unpaid fines
	fine_filters = {"paid": 0}
	if vehicle:
		fine_filters["vehicle"] = vehicle

	report["traffic_fines"] = frappe.get_all(
		"Traffic Fine",
		filters=fine_filters,
		fields=["name", "vehicle", "fine_date", "fine_number", "amount",
		        "charged_to_customer", "linked_contract", "linked_agreement", "source"],
		order_by="fine_date desc"
	)

	# Calculate summary
	report["summary"] = {
		"total_salik": sum([flt(t["toll_amount"]) for t in report["salik_transactions"]]),
		"total_fines": sum([flt(f["amount"]) for f in report["traffic_fines"]]),
		"count_salik": len(report["salik_transactions"]),
		"count_fines": len(report["traffic_fines"])
	}
	report["summary"]["grand_total"] = report["summary"]["total_salik"] + report["summary"]["total_fines"]

	return report
