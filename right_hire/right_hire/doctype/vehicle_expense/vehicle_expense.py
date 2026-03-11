# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class VehicleExpense(Document):
	def validate(self):
		self.calculate_item_amounts()
		self.calculate_vat()
		self.calculate_total()

	def calculate_item_amounts(self):
		"""Calculate VAT and total for each expense item"""
		if self.expense_items:
			for item in self.expense_items:
				if item.amount_before_vat and item.vat_rate:
					item.vat_amount = flt(item.amount_before_vat) * flt(item.vat_rate) / 100
					item.total_amount = flt(item.amount_before_vat) + flt(item.vat_amount)
				else:
					item.vat_amount = 0
					item.total_amount = flt(item.amount_before_vat)

	def calculate_vat(self):
		"""Calculate VAT amount based on amount before VAT and VAT rate"""
		# If using child table, calculate from items
		if self.expense_items:
			self.amount_before_vat = sum([flt(item.amount_before_vat) for item in self.expense_items])
			self.vat_amount = sum([flt(item.vat_amount) for item in self.expense_items])
		elif self.amount_before_vat and self.vat_rate:
			self.vat_amount = flt(self.amount_before_vat) * flt(self.vat_rate) / 100
		else:
			self.vat_amount = 0

	def calculate_total(self):
		"""Calculate total amount including VAT"""
		# If using child table, calculate from items
		if self.expense_items:
			self.total_amount = sum([flt(item.total_amount) for item in self.expense_items])
		else:
			self.total_amount = flt(self.amount_before_vat) + flt(self.vat_amount)

	@frappe.whitelist()
	def create_purchase_invoice(self):
		"""Create a Purchase Invoice for this expense"""
		if self.purchase_invoice:
			frappe.throw(f"Purchase Invoice {self.purchase_invoice} already exists for this expense")

		if not self.supplier:
			frappe.throw("Please select a Supplier before creating Purchase Invoice")

		# Get or create expense item
		expense_item = self.get_or_create_expense_item()

		# Create Purchase Invoice
		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"supplier": self.supplier,
			"posting_date": self.expense_date,
			"bill_no": self.receipt_number,
			"company": self.company or frappe.defaults.get_defaults().get("company"),
			"items": [{
				"item_code": expense_item,
				"item_name": f"{self.expense_type} - {self.vehicle_name}",
				"description": self.description or f"{self.expense_type} for {self.vehicle_name}",
				"qty": 1,
				"rate": self.amount_before_vat,
				"cost_center": self.cost_center
			}],
			"taxes": [{
				"charge_type": "On Net Total",
				"account_head": self.get_vat_account(),
				"description": f"VAT @ {self.vat_rate}%",
				"rate": self.vat_rate
			}]
		})

		pi.insert()

		# Link back to this expense
		self.purchase_invoice = pi.name
		self.status = "Paid"
		self.save()

		frappe.msgprint(f"Purchase Invoice {pi.name} created successfully")

		return pi.name

	def get_or_create_expense_item(self):
		"""Get or create an item for this expense type"""
		item_code = f"VE-{self.expense_type}".replace(" ", "-")

		if not frappe.db.exists("Item", item_code):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": f"Vehicle Expense - {self.expense_type}",
				"item_group": "Services",
				"stock_uom": "Unit",
				"is_stock_item": 0,
				"is_sales_item": 0,
				"is_purchase_item": 1,
				"is_fixed_asset": 0
			})
			item.insert(ignore_permissions=True)

		return item_code

	def get_vat_account(self):
		"""Get the VAT account for purchase"""
		# Try to get from company
		company = self.company or frappe.defaults.get_defaults().get("company")

		# Look for a VAT/Tax account
		vat_account = frappe.db.get_value(
			"Account",
			{
				"company": company,
				"account_type": "Tax",
				"is_group": 0
			},
			"name"
		)

		if not vat_account:
			frappe.throw("Please set up a Tax Account for VAT in Chart of Accounts")

		return vat_account
