import frappe


DEFAULT_BANK_ACCOUNT = "Right Hire Car Rental LLC - Mashreq Bank"

DEFAULT_INVOICE_TERMS = [
	"Payment is due within 30 days of invoice date.",
	"All disputes must be raised within 7 days of invoice receipt.",
]


def get_bank_details_html(bank_account_name):
	"""Build HTML string from Bank Account details"""
	if not bank_account_name or not frappe.db.exists("Bank Account", bank_account_name):
		return ""

	ba = frappe.get_doc("Bank Account", bank_account_name)
	parts = []
	if ba.bank:
		parts.append(f"<b>Bank Name:</b> {ba.bank}")
	if ba.account_name:
		parts.append(f"<b>Account Name:</b> {ba.account_name}")
	if ba.bank_account_no:
		parts.append(f"<b>Account No:</b> {ba.bank_account_no}")
	if ba.iban:
		parts.append(f"<b>IBAN:</b> {ba.iban}")
	# SWIFT is on the Bank doctype, not Bank Account
	if ba.bank:
		swift = frappe.db.get_value("Bank", ba.bank, "swift_number")
		if swift:
			parts.append(f"<b>SWIFT Code:</b> {swift}")
	if getattr(ba, "branch_code", None):
		parts.append(f"<b>Branch:</b> {ba.branch_code}")

	return "<br>".join(parts)


def set_invoice_defaults(doc, method=None):
	"""Set default bank account, bank details, and invoice terms on new Sales Invoices"""
	if not doc.bank_account:
		doc.bank_account = DEFAULT_BANK_ACCOUNT

	if not doc.bank_details_html and doc.bank_account:
		doc.bank_details_html = get_bank_details_html(doc.bank_account)

	if not doc.invoice_terms:
		for term_text in DEFAULT_INVOICE_TERMS:
			doc.append("invoice_terms", {"term": term_text})


@frappe.whitelist()
def fetch_bank_details(bank_account):
	"""API endpoint for client script to fetch bank details HTML"""
	return get_bank_details_html(bank_account)
