# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, nowdate, flt

class SalikTransaction(Document):
	def before_save(self):
		# Auto-link to active contract/agreement for the vehicle
		if not self.linked_contract and not self.linked_agreement:
			self.auto_link_contract()

		# Determine charge type based on whether vehicle was with customer
		self.determine_charge_type()

		# Calculate customer charge amount with excess/markup
		self.calculate_customer_charge_amount()

		# Auto-mark as company expense if no agreement linked
		self.update_company_expense_status()

	def after_insert(self):
		# Create Journal Entry for company expenses
		self.create_journal_entry_if_needed()

	def on_update(self):
		# Create Journal Entry if marked as company expense and no JE exists
		if not self.flags.in_insert:
			self.create_journal_entry_if_needed()

	def determine_charge_type(self):
		"""Set charge_type based on whether vehicle was actually with customer at transaction time."""
		# If no agreement linked, it's non-revenue (company expense)
		if not self.linked_contract and not self.linked_agreement:
			self.charge_type = "Non-Revenue"
			return

		# Build transaction datetime
		if self.transaction_time:
			trans_datetime = get_datetime(f"{self.transaction_date} {self.transaction_time}")
		else:
			trans_datetime = get_datetime(self.transaction_date)

		# Check if vehicle was with customer at that exact time
		agreement_type = "Lease Agreement" if self.linked_contract else "Rental Agreement"
		agreement_name = self.linked_contract or self.linked_agreement

		if self._was_vehicle_with_customer(trans_datetime, agreement_type, agreement_name):
			self.charge_type = "Revenue"
		else:
			self.charge_type = "Non-Revenue"

	def calculate_customer_charge_amount(self):
		"""Calculate the amount to charge customer including excess/markup from agreement"""
		if not self.toll_amount:
			return

		salik_percentage = 0

		# Get salik percentage from linked Lease Agreement
		if self.linked_contract:
			salik_percentage = flt(frappe.db.get_value(
				"Lease Agreement", self.linked_contract, "salik_percentage"
			))

		# Get salik percentage from linked Rental Agreement
		elif self.linked_agreement:
			salik_percentage = flt(frappe.db.get_value(
				"Rental Agreement", self.linked_agreement, "salik_percentage"
			))

		# Calculate customer charge amount: toll_amount + markup
		if self.linked_contract or self.linked_agreement:
			markup_amount = flt(self.toll_amount) * flt(salik_percentage) / 100
			self.customer_charge_amount = flt(self.toll_amount) + markup_amount
		else:
			# No agreement linked - no customer charge
			self.customer_charge_amount = 0

	def update_company_expense_status(self):
		"""Auto-set is_company_expense when no agreement is linked"""
		if not self.linked_contract and not self.linked_agreement:
			if not self.is_company_expense:
				self.is_company_expense = 1
				# Set default accounts from Salik Settings
				self._set_default_accounts()
		else:
			# If linked to an agreement, it's not a company expense
			self.is_company_expense = 0
			self.journal_entry = None

	def _set_default_accounts(self):
		"""Set default accounting values from Salik Settings"""
		settings = frappe.get_cached_doc("Salik Settings")

		if settings.default_company and not self.company:
			self.company = settings.default_company

		if settings.default_expense_account and not self.expense_account:
			self.expense_account = settings.default_expense_account

		if settings.default_cost_center and not self.cost_center:
			self.cost_center = settings.default_cost_center

	def create_journal_entry_if_needed(self):
		"""Create Journal Entry for company expense if enabled in settings"""
		if not self.is_company_expense:
			return

		if self.journal_entry:
			return

		settings = frappe.get_cached_doc("Salik Settings")

		if not settings.auto_create_journal_entry:
			return

		if not self.expense_account or not settings.default_credit_account:
			frappe.msgprint(
				f"Cannot create Journal Entry for {self.name}: Missing expense account or credit account configuration",
				alert=True
			)
			return

		company = self.company or settings.default_company
		if not company:
			frappe.msgprint(
				f"Cannot create Journal Entry for {self.name}: Company not specified",
				alert=True
			)
			return

		try:
			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Journal Entry"
			je.company = company
			je.posting_date = self.transaction_date or nowdate()
			je.user_remark = f"Salik toll expense for vehicle {self.plate_number or self.vehicle} - {self.gate_location or ''}"

			# Debit: Expense Account
			je.append("accounts", {
				"account": self.expense_account,
				"debit_in_account_currency": self.toll_amount,
				"cost_center": self.cost_center,
				"user_remark": f"Salik Transaction: {self.name}"
			})

			# Credit: Cash/Bank/Prepaid Account
			je.append("accounts", {
				"account": settings.default_credit_account,
				"credit_in_account_currency": self.toll_amount,
				"cost_center": self.cost_center
			})

			je.insert(ignore_permissions=True)
			je.submit()

			# Update the Salik Transaction with the Journal Entry reference
			frappe.db.set_value("Salik Transaction", self.name, "journal_entry", je.name, update_modified=False)
			self.journal_entry = je.name

			frappe.msgprint(f"Journal Entry {je.name} created for Salik toll expense", alert=True)

		except Exception as e:
			frappe.log_error(
				f"Failed to create Journal Entry for Salik Transaction {self.name}: {str(e)}",
				"Salik Transaction JE Error"
			)

	def auto_link_contract(self):
		"""Auto-link to active contract or agreement based on movement times"""
		if not self.vehicle or not self.transaction_date:
			return

		# Build full transaction datetime for precise checking
		trans_date = getdate(self.transaction_date)
		if self.transaction_time:
			trans_datetime = get_datetime(f"{self.transaction_date} {self.transaction_time}")
		else:
			trans_datetime = get_datetime(self.transaction_date)

		# Check for Lease Agreement where vehicle was with customer at transaction time
		lease_agreement = self._find_active_lease(trans_datetime)
		if lease_agreement:
			self.linked_contract = lease_agreement
			return

		# Check for Rental Agreement where vehicle was with customer at transaction time
		rental_agreement = self._find_active_rental(trans_datetime)
		if rental_agreement:
			self.linked_agreement = rental_agreement

	def _find_active_lease(self, trans_datetime):
		"""Find lease agreement where vehicle was actually with customer at given datetime"""
		trans_date = trans_datetime.date() if hasattr(trans_datetime, 'date') else getdate(trans_datetime)

		# Get potential lease agreements for this vehicle on this date
		lease_agreements = frappe.get_all(
			"Lease Agreement",
			filters={
				"vehicle": self.vehicle,
				"start_date": ["<=", trans_date],
				"docstatus": ["!=", 2]
			},
			fields=["name", "start_date", "end_date"],
			order_by="start_date desc"
		)

		for la in lease_agreements:
			# Check end_date
			if la.end_date and getdate(la.end_date) < trans_date:
				continue

			# Check if vehicle was actually with customer at this time via Movement records
			if self._was_vehicle_with_customer(trans_datetime, "Lease Agreement", la.name):
				return la.name

		return None

	def _find_active_rental(self, trans_datetime):
		"""Find rental agreement where vehicle was actually with customer at given datetime"""
		# Check rental agreements using datetime comparison
		rental_agreements = frappe.db.sql("""
			SELECT name, start_datetime, end_datetime, actual_return_datetime
			FROM `tabRental Agreement`
			WHERE vehicle = %s
			AND start_datetime <= %s
			AND docstatus != 2
			ORDER BY start_datetime DESC
		""", (self.vehicle, trans_datetime), as_dict=True)

		for ra in rental_agreements:
			# Check if transaction is before return
			end_dt = ra.actual_return_datetime or ra.end_datetime
			if end_dt and get_datetime(end_dt) < trans_datetime:
				continue

			# Check if vehicle was actually with customer at this time
			if self._was_vehicle_with_customer(trans_datetime, "Rental Agreement", ra.name):
				return ra.name

		return None

	def _was_vehicle_with_customer(self, check_datetime, agreement_type, agreement_name):
		"""Check if vehicle was with customer at the given datetime based on movement records"""
		# Find the most recent OUT movement before the check time
		out_movement = frappe.db.sql("""
			SELECT name, out_date_time, in_date_time, status
			FROM `tabMovements`
			WHERE vehicle = %s
			AND agreement_type = %s
			AND agreement_no = %s
			AND out_date_time <= %s
			AND status IN ('Out Only', 'Completed', 'In Transit')
			ORDER BY out_date_time DESC
			LIMIT 1
		""", (self.vehicle, agreement_type, agreement_name, check_datetime), as_dict=True)

		if not out_movement:
			# No movement record found - vehicle wasn't delivered yet
			return False

		mov = out_movement[0]

		# If vehicle was returned before the check time, it wasn't with customer
		if mov.in_date_time and get_datetime(mov.in_date_time) <= check_datetime:
			return False

		# Vehicle was out and not yet returned at the check time
		return True
