import frappe
from frappe.model.document import Document
from frappe.utils import flt, add_months, getdate


class LeaseQuotation(Document):
	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		"""Validate dates."""
		# Auto-set valid_until if not set (7 days from quotation date)
		if not self.valid_until:
			from frappe.utils import add_days
			self.valid_until = add_days(self.quotation_date, 7)

	@frappe.whitelist()
	def generate_lease_contract(self):
		"""Generate Lease Contract from selected quotation item."""
		# Return items for selection dialog
		if not self.quotation_items:
			frappe.throw("No quotation items found. Please add at least one vehicle option.")

		items = []
		for item in self.quotation_items:
			items.append({
				"vehicle": item.vehicle,
				"annual_mileage": item.annual_mileage,
				"price_per_month": item.price_per_month
			})

		return {
			"items": items,
			"customer": self.customer,
			"driver": self.driver,
			"branch": self.branch,
			"quotation": self.name
		}

	@frappe.whitelist()
	def create_contract_from_item(self, item_idx):
		"""Create Lease Contract from a specific quotation item"""
		if self.lease_agreement:
			frappe.throw(f"Lease Agreement {self.lease_agreement} already generated from this quotation")

		if self.quotation_status not in ["Sent", "Draft"]:
			if self.quotation_status == "Accepted":
				frappe.throw("This quotation has already been accepted and a contract generated")
			else:
				frappe.throw(f"Cannot generate contract from {self.quotation_status} quotation")

		# Validate required fields
		if not self.customer:
			frappe.throw("Customer is required to generate lease contract")

		item_idx = int(item_idx)
		if item_idx < 0 or item_idx >= len(self.quotation_items):
			frappe.throw("Invalid item selection")

		selected_item = self.quotation_items[item_idx]

		# Calculate default dates - use lease_duration_months from parent if available
		from frappe.utils import nowdate, add_months
		start_date = nowdate()
		duration_months = self.lease_duration_months or 12
		end_date = add_months(start_date, duration_months)

		# Create lease contract
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"quotation": self.name,
			"customer": self.customer,
			"driver": self.driver,
			"vehicle": selected_item.vehicle,
			"start_date": start_date,
			"end_date": end_date,
			"billing_cycle": "Monthly",  # Default to monthly
			"billing_day": 1,  # Default to 1st of month
			"monthly_rate": selected_item.price_per_month,
			"km_allowance_monthly": (selected_item.annual_mileage / 12) if selected_item.annual_mileage else None,
			"branch": self.branch,
			"lease_status": "Draft"
		})

		contract.insert()

		# Update quotation
		self.quotation_status = "Accepted"
		self.lease_agreement = contract.name
		self.generated_on = frappe.utils.now()
		self.save()

		frappe.msgprint(f"Lease Contract {contract.name} created successfully")

		return {
			"success": True,
			"contract": contract.name
		}
