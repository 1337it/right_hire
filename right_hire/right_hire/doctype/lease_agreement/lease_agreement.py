# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import calendar
import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_months, add_days, nowdate
from frappe import _
from dateutil.relativedelta import relativedelta

class LeaseAgreement(Document):
	def validate(self):
		self.validate_lease_status()
		self.validate_dates()
		self.calculate_tenure()
		self.calculate_grand_total()
		self.calculate_totals()

	def validate_lease_status(self):
		"""Ensure lease_status matches document status"""
		# If document is draft, lease_status must be Draft
		if self.docstatus == 0:
			if self.lease_status != "Draft":
				self.lease_status = "Draft"
		# If document is being submitted, automatically set to Active
		elif self.docstatus == 1:
			if self.lease_status == "Draft":
				self.lease_status = "Active"

	def calculate_grand_total(self):
		"""Calculate grand total from charges"""
		# Calculate rent total: monthly_rate * tenure_months
		rent_total = flt(self.monthly_rate or 0) * flt(self.tenure_months or 0)

		# Sum all charges
		subtotal = (
			rent_total +
			flt(self.cdw_amount or 0) +
			flt(self.fuel_charges or 0) +
			flt(self.mileage_charges or 0) +
			flt(self.additional_driver_charges or 0) +
			flt(self.extra_charges or 0) -
			flt(self.discount_amount or 0)
		)

		# Calculate tax
		tax_rate = flt(self.tax_percentage or 0) / 100
		self.tax_amount = flt(subtotal * tax_rate, 2)

		# Grand total
		self.grand_total = flt(subtotal + self.tax_amount, 2)

	def validate_dates(self):
		"""Validate start and end dates"""
		# Only validate if both dates are set
		if self.start_date and self.end_date:
			if getdate(self.end_date) <= getdate(self.start_date):
				frappe.throw(_("End date must be after start date"))

	def calculate_tenure(self):
		"""Calculate tenure in months"""
		if not self.start_date or not self.end_date:
			return

		start = getdate(self.start_date)
		end = getdate(self.end_date)
		delta = relativedelta(end, start)
		self.tenure_months = delta.months + (delta.years * 12)

	def calculate_totals(self):
		"""Calculate financial totals from schedule"""
		if not self.invoice_schedule:
			return

		self.total_invoiced = sum(
			flt(line.amount) for line in self.invoice_schedule
			if line.status in ["Invoiced", "Paid"]
		)

		# Calculate total paid from linked invoices
		self.total_paid = self.get_total_paid()
		self.total_outstanding = flt(self.total_invoiced) - flt(self.total_paid)

	def get_total_paid(self):
		"""Get total paid amount from linked Sales Invoices"""
		if not frappe.db.exists("DocType", "Sales Invoice"):
			return 0

		invoices = frappe.db.get_all(
			"Sales Invoice",
			filters={"lease_agreement": self.name, "docstatus": 1},
			pluck="name"
		)

		total = 0
		for invoice_name in invoices:
			invoice = frappe.get_doc("Sales Invoice", invoice_name)
			total += flt(invoice.grand_total) - flt(invoice.outstanding_amount)

		return total

	def on_submit(self):
		"""Generate invoice schedule on submission"""
		# Set lease status to Active
		self.db_set("lease_status", "Active")

		self.generate_invoice_schedule()
		self.update_vehicle_status("Leased")

		# Create first invoice if billing day is today or past
		if self.billing_day <= getdate(nowdate()).day:
			self.create_first_invoice()

	def on_cancel(self):
		"""Cancel lease and update vehicle"""
		self.db_set("lease_status", "Cancelled")
		self.update_vehicle_status("Available")
		self.cancel_pending_invoices()

	def generate_invoice_schedule(self):
		"""Generate invoice schedule based on billing cycle

		First invoice: From start_date to the day before billing_day (pro-rated)
		Subsequent invoices: From billing_day to next billing_day - 1 (full periods)
		"""
		if self.invoice_schedule:
			# Schedule already exists
			return

		self.invoice_schedule = []

		billing_day = self.billing_day or 1  # Default to 1st if not set
		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)

		# Helper function to get billing day date for a given month
		def get_billing_date(year, month, day):
			max_day = calendar.monthrange(year, month)[1]
			actual_day = min(day, max_day)
			return start_date.replace(year=year, month=month, day=actual_day)

		# Calculate the first billing date after start_date
		first_billing_year = start_date.year
		first_billing_month = start_date.month

		# Check if billing day is after start day in the same month
		max_day_in_start_month = calendar.monthrange(first_billing_year, first_billing_month)[1]
		actual_billing_day_in_start_month = min(billing_day, max_day_in_start_month)

		if start_date.day < actual_billing_day_in_start_month:
			# Billing day is later this month
			first_billing_date = start_date.replace(day=actual_billing_day_in_start_month)
		else:
			# Billing day already passed, go to next month
			next_month = add_months(start_date, 1)
			max_day_next = calendar.monthrange(next_month.year, next_month.month)[1]
			first_billing_date = next_month.replace(day=min(billing_day, max_day_next))

		# First invoice: From start_date to day before first billing date (pro-rated)
		first_period_end = add_days(first_billing_date, -1)

		# Calculate pro-rated amount for first period
		# Month is always 30 days. If lease starts on 2nd, that's 28 days (30 - 2)
		days_in_first_period = 30 - start_date.day
		daily_rate = flt(self.monthly_rate) / 30
		first_amount = flt(daily_rate * days_in_first_period)

		self.append("invoice_schedule", {
			"period_start": start_date,
			"period_end": first_period_end,
			"invoice_date": add_days(first_period_end, 1),  # Invoice day after period ends (in arrears)
			"amount": round(first_amount, 2),
			"status": "Pending"
		})

		# Subsequent invoices: Full billing cycles
		current_billing_date = first_billing_date

		while current_billing_date <= end_date:
			period_start = current_billing_date

			# Calculate next billing date
			next_billing = add_months(current_billing_date, 1)
			max_day_next = calendar.monthrange(next_billing.year, next_billing.month)[1]
			next_billing_date = next_billing.replace(day=min(billing_day, max_day_next))

			# Period end is day before next billing date, but not beyond end_date
			period_end = add_days(next_billing_date, -1)

			if period_start > end_date:
				break

			if period_end > end_date:
				# Last period - pro-rate using end_date day as days used
				period_end = end_date
				days_in_period = period_end.day
				amount = round(flt(daily_rate * days_in_period), 2)
			else:
				# Full month
				amount = flt(self.monthly_rate)

			self.append("invoice_schedule", {
				"period_start": period_start,
				"period_end": period_end,
				"invoice_date": add_days(period_end, 1),  # Invoice day after period ends (in arrears)
				"amount": amount,
				"status": "Pending"
			})

			current_billing_date = next_billing_date

		self.save()

	def create_first_invoice(self):
		"""Create first invoice if due"""
		if not self.invoice_schedule:
			return

		first_line = self.invoice_schedule[0]
		if first_line.status == "Pending":
			try:
				self.create_monthly_invoice(first_line)
			except Exception as e:
				frappe.log_error(f"Failed to create first invoice: {str(e)}", "Lease Contract First Invoice")

	@frappe.whitelist()
	def create_monthly_invoice(self, schedule_line=None):
		"""Create Sales Invoice for a billing period"""
		import traceback

		if not frappe.db.exists("DocType", "Sales Invoice"):
			frappe.throw(_("ERPNext Sales Invoice not available"))

		# If schedule_line is passed as row name, fetch it
		if isinstance(schedule_line, str):
			for line in self.invoice_schedule:
				if line.name == schedule_line:
					schedule_line = line
					break

		if not schedule_line:
			frappe.throw(_("No schedule line provided"))

		# Check if already invoiced
		if schedule_line.status != "Pending":
			frappe.msgprint(_(f"This period is already {schedule_line.status}"))
			return schedule_line.invoice_ref

		try:
			# Ensure rental service item exists
			self.ensure_rental_service_item()

			# Get company
			company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

			# Create Sales Invoice
			invoice = frappe.new_doc("Sales Invoice")
			invoice.customer = self.customer
			invoice.posting_date = getdate()
			invoice.due_date = getdate()
			invoice.company = company

			# Set currency and conversion rate
			invoice.currency = frappe.db.get_value("Company", company, "default_currency") or "AED"
			invoice.conversion_rate = 1.0

			# Set selling price list
			invoice.selling_price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"

			# Set debit_to account
			invoice.debit_to = frappe.db.get_value("Company", company, "default_receivable_account")

			# Set customer defaults if missing
			customer_group = frappe.db.get_value("Customer", self.customer, "customer_group")
			if not customer_group:
				customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
			invoice.customer_group = customer_group

			territory = frappe.db.get_value("Customer", self.customer, "territory")
			if not territory:
				territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
			invoice.territory = territory

			# Set custom fields
			invoice.rental_type = self.billing_cycle + " Lease"
			invoice.vehicle = self.vehicle
			invoice.lease_agreement = self.name

			# Set cost center from branch
			if self.branch:
				cost_center = frappe.db.get_value("Branch", self.branch, "cost_center")
				if cost_center:
					invoice.cost_center = cost_center

			# Add lease rental line item
			income_account = self.get_income_account(invoice.company)
			invoice.append("items", {
				"item_code": "Rental Service",
				"item_name": f"Lease Rental - {self.vehicle}",
				"description": f"Lease Contract {self.name} - Period: {schedule_line.period_start} to {schedule_line.period_end}",
				"qty": 1,
				"rate": flt(schedule_line.amount),
				"amount": flt(schedule_line.amount),
				"income_account": income_account,
			})

			# Add KM overage if applicable
			overage = self.calculate_km_overage(schedule_line)
			if overage and flt(overage.get("amount", 0)) > 0:
				invoice.append("items", {
					"item_code": "Rental Service",
					"item_name": "KM Overage",
					"description": f"{overage['km']} KM overage @ {overage['rate']} per KM",
					"qty": flt(overage["km"]),
					"rate": flt(overage["rate"]),
					"amount": flt(overage["amount"]),
					"income_account": self.get_overage_account(invoice.company),
				})

			# Add Salik charges for the billing period
			salik_items = self.get_salik_charges_for_period(schedule_line.period_start, schedule_line.period_end, invoice.company)
			for item in (salik_items or []):
				invoice.append("items", item)

			# Add Darb charges for the billing period
			darb_items = self.get_darb_charges_for_period(schedule_line.period_start, schedule_line.period_end, invoice.company)
			for item in (darb_items or []):
				invoice.append("items", item)

			# Add Traffic Fines for the billing period
			fine_items = self.get_traffic_fines_for_period(schedule_line.period_start, schedule_line.period_end, invoice.company)
			for item in (fine_items or []):
				invoice.append("items", item)

			# Set default bank account and invoice terms
			from right_hire.right_hire.invoice_defaults import set_invoice_defaults, DEFAULT_BANK_ACCOUNT
			invoice.bank_account = DEFAULT_BANK_ACCOUNT
			set_invoice_defaults(invoice)

			# Set flags to bypass certain validations
			invoice.flags.ignore_mandatory = True

			# Save and submit using standard ERPNext flow
			invoice.save(ignore_permissions=True)
			invoice.submit()

			# Update schedule line directly in database (bypass submit validation)
			# Note: invoice_date stays as the original scheduled date, not today's date
			frappe.db.set_value("Lease Schedule Line", schedule_line.name, {
				"status": "Invoiced",
				"invoice_ref": invoice.name
			}, update_modified=False)

			# Back-fill invoice_reference on charged Salik/Darb/Fine transactions
			for dt in ("Salik Transaction", "Darb Transaction", "Traffic Fine"):
				frappe.db.sql("""
					UPDATE `tab{dt}` SET invoice_reference = %s
					WHERE linked_contract = %s AND charged_to_customer = 1
					AND (invoice_reference IS NULL OR invoice_reference = '')
				""".format(dt=dt), (invoice.name, self.name))

			frappe.msgprint(_(f"Invoice {invoice.name} created successfully"), indicator="green")
			return invoice.name

		except Exception as e:
			frappe.log_error(
				f"Invoice creation failed for {self.name}:\n{traceback.format_exc()}",
				"Lease Invoice Creation Error"
			)
			raise

	def calculate_km_overage(self, schedule_line):
		"""Calculate KM overage for a period"""
		if not self.km_allowance_monthly or not self.overage_per_km:
			return None

		# Get vehicle odometer readings for the period
		period_start = getdate(schedule_line.period_start)
		period_end = getdate(schedule_line.period_end)

		# Ensure valid dates
		if not period_start or not period_end:
			return None

		# Calculate months in period
		delta = relativedelta(period_end, period_start)
		months = flt(delta.months) + 1

		allowance = flt(self.km_allowance_monthly) * flt(months)

		# Get actual KM from vehicle movements or odometer logs
		actual_km = flt(self.get_actual_km_for_period(period_start, period_end))

		if actual_km > allowance:
			overage_km = flt(actual_km) - flt(allowance)
			overage_rate = flt(self.overage_per_km)
			return {
				"km": overage_km,
				"rate": overage_rate,
				"amount": flt(overage_km) * flt(overage_rate)
			}

		return None

	def get_actual_km_for_period(self, start_date, end_date):
		"""Get actual KM driven in period - simplified version"""
		# In production, implement proper odometer logging
		# For now, return 0 to avoid overage charges without proper tracking
		return 0

	def get_salik_charges_for_period(self, period_start, period_end, company):
		"""Get unbilled Salik charges for the billing period, grouped by toll schedule"""
		from collections import defaultdict
		items = []

		if not self.vehicle:
			return items

		# Salik markup percentage (10%)
		SALIK_MARKUP_PERCENT = 10

		# Fixed rates by schedule
		SALIK_RATES = {
			"Peak": 6.00,
			"Low-Peak": 4.00,
			"Off-Peak": 0.00
		}

		# Find Salik transactions for this vehicle in the period that are not yet invoiced
		# Only include Revenue transactions (vehicle was with customer at transaction time)
		salik_transactions = frappe.get_all(
			"Salik Transaction",
			filters={
				"vehicle": self.vehicle,
				"transaction_date": ["between", [getdate(period_start), getdate(period_end)]],
				"linked_contract": self.name,
				"charged_to_customer": 0,
				"charge_type": "Revenue"
			},
			fields=["name", "transaction_date", "gate_location", "toll_amount", "toll_schedule"]
		)

		# Also get unlinked Revenue transactions for the vehicle
		unlinked_transactions = frappe.get_all(
			"Salik Transaction",
			filters={
				"vehicle": self.vehicle,
				"transaction_date": ["between", [getdate(period_start), getdate(period_end)]],
				"linked_contract": ["is", "not set"],
				"linked_agreement": ["is", "not set"],
				"charged_to_customer": 0,
				"charge_type": "Revenue"
			},
			fields=["name", "transaction_date", "gate_location", "toll_amount", "toll_schedule"]
		)

		all_transactions = salik_transactions + unlinked_transactions

		if not all_transactions:
			return items

		# Group transactions by toll schedule
		grouped = defaultdict(lambda: {"count": 0, "transactions": []})
		for t in all_transactions:
			schedule = t.get("toll_schedule") or "Peak"
			grouped[schedule]["count"] += 1
			grouped[schedule]["transactions"].append(t.name)

		income_account = self.get_salik_income_account(company)

		schedule_order = ["Peak", "Low-Peak", "Off-Peak"]

		for schedule in schedule_order:
			if schedule not in grouped:
				continue

			data = grouped[schedule]
			if data["count"] == 0:
				continue

			base_rate = SALIK_RATES.get(schedule, 4.00)

			# Skip Off-Peak (free) trips
			if base_rate == 0:
				for trans_name in data["transactions"]:
					frappe.db.set_value("Salik Transaction", trans_name, {
						"linked_contract": self.name,
						"charged_to_customer": 1,
						"customer_charged_date": nowdate()
					}, update_modified=False)
				continue

			rate_with_markup = flt(base_rate * (1 + SALIK_MARKUP_PERCENT / 100), 2)
			amount = flt(rate_with_markup * data["count"], 2)

			items.append({
				"item_code": "Rental Service",
				"item_name": f"Salik Toll - {schedule}",
				"description": f"Salik Toll - {schedule}",
				"qty": data["count"],
				"rate": rate_with_markup,
				"amount": amount,
				"income_account": income_account,
			})

			# Mark transactions as invoiced and link to contract
			for trans_name in data["transactions"]:
				frappe.db.set_value("Salik Transaction", trans_name, {
					"linked_contract": self.name,
					"charged_to_customer": 1,
					"customer_charged_date": nowdate()
				}, update_modified=False)

		return items

	def get_darb_charges_for_period(self, period_start, period_end, company):
		"""Get unbilled Darb toll charges for the billing period (amount + 10% markup)"""
		items = []

		if not self.vehicle:
			return items

		DARB_MARKUP_PERCENT = 10

		# Find Darb transactions linked to this contract or unlinked
		darb_transactions = frappe.get_all(
			"Darb Transaction",
			filters={
				"vehicle": self.vehicle,
				"transaction_date": ["between", [getdate(period_start), getdate(period_end)]],
				"linked_contract": self.name,
				"charged_to_customer": 0,
				"charge_type": "Revenue"
			},
			fields=["name", "transaction_date", "gate_location", "toll_amount"]
		)

		unlinked_transactions = frappe.get_all(
			"Darb Transaction",
			filters={
				"vehicle": self.vehicle,
				"transaction_date": ["between", [getdate(period_start), getdate(period_end)]],
				"linked_contract": ["is", "not set"],
				"linked_agreement": ["is", "not set"],
				"charged_to_customer": 0,
				"charge_type": "Revenue"
			},
			fields=["name", "transaction_date", "gate_location", "toll_amount"]
		)

		all_transactions = darb_transactions + unlinked_transactions

		if not all_transactions:
			return items

		income_account = self.get_darb_income_account(company)

		total_base = sum(flt(t.toll_amount) for t in all_transactions)
		total_with_markup = flt(total_base * (1 + DARB_MARKUP_PERCENT / 100), 2)

		items.append({
			"item_code": "Rental Service",
			"item_name": "Darb Toll Charges",
			"description": f"Darb Toll - {len(all_transactions)} trip(s) (base AED {total_base:.2f} + 10% admin)",
			"qty": len(all_transactions),
			"rate": flt(total_with_markup / len(all_transactions), 2),
			"amount": total_with_markup,
			"income_account": income_account,
		})

		# Mark transactions as invoiced
		for t in all_transactions:
			frappe.db.set_value("Darb Transaction", t.name, {
				"linked_contract": self.name,
				"charged_to_customer": 1,
				"customer_charge_amount": flt(flt(t.toll_amount) * (1 + DARB_MARKUP_PERCENT / 100), 2),
				"customer_charged_date": nowdate()
			}, update_modified=False)

		return items

	def get_darb_income_account(self, company):
		"""Get income account for Darb charges"""
		# Use same account as Salik, or fallback to default
		account = frappe.db.get_value("Salik Settings", "Salik Settings", "customer_charge_account")
		if account:
			return account
		return frappe.db.get_value("Company", company, "default_income_account")

	def get_traffic_fines_for_period(self, period_start, period_end, company):
		"""Get unbilled Traffic Fines for the billing period"""
		items = []

		if not self.vehicle:
			return items

		# Get fine markup from agreement - ensure it's a float
		fine_markup = flt(self.excess_per_traffic_fine) if self.excess_per_traffic_fine else 0.0
		knowledge_fee = flt(self.knowledge_fee_per_fine) if self.knowledge_fee_per_fine else 0.0

		# fine_date is a Data field stored as dd/mm/yyyy, so SQL date comparisons don't work.
		# Fetch all uncharged fines for the vehicle and filter by date in Python.
		all_fines = frappe.get_all(
			"Traffic Fine",
			filters={
				"vehicle": self.vehicle,
				"charged_to_customer": 0
			},
			fields=["name", "fine_date", "details", "amount", "location"]
		)

		p_start = getdate(period_start)
		p_end = getdate(period_end)
		fines = []
		for f in all_fines:
			parsed = self._parse_fine_date(f.fine_date)
			if parsed and p_start <= parsed <= p_end:
				fines.append(f)

		if not fines:
			return items

		income_account = self.get_fines_income_account(company)

		# Add each fine as a separate line item
		for fine in fines:
			fine_amount = flt(fine.get("amount")) if fine.get("amount") else 0.0
			total_with_markup = flt(fine_amount) + flt(fine_markup)

			desc_parts = [f"Fine Date: {fine.get('fine_date')}", f"Location: {fine.get('location', 'N/A')}", f"Base: AED {fine_amount:.2f}"]
			if fine_markup > 0:
				desc_parts.append(f"+ AED {fine_markup:.2f} admin fee")

			items.append({
				"item_code": "Rental Service",
				"item_name": f"Traffic Fine - {fine.get('details', 'Violation')[:50]}",
				"description": "\n".join(desc_parts),
				"qty": 1,
				"rate": flt(total_with_markup),
				"amount": flt(total_with_markup),
				"income_account": income_account,
			})

			# Mark fine as invoiced and link to agreement
			frappe.db.set_value("Traffic Fine", fine.name, {
				"linked_contract": self.name,
				"charged_to_customer": 1,
				"customer_charged_date": nowdate()
			}, update_modified=False)

		# Add Knowledge Fee as a single line item for all fines in the period
		if knowledge_fee > 0 and fines:
			items.append({
				"item_code": "Rental Service",
				"item_name": "Knowledge Fee - Traffic Fines",
				"description": f"Knowledge Fee @ AED {knowledge_fee:.2f} x {len(fines)} fine(s)",
				"qty": len(fines),
				"rate": flt(knowledge_fee),
				"amount": flt(knowledge_fee * len(fines)),
				"income_account": income_account,
			})

		return items

	@staticmethod
	def _parse_fine_date(date_str):
		"""Parse fine_date Data field (dd/mm/yyyy, YYYY-MM-DD, or dd Mon YYYY)."""
		if not date_str:
			return None
		from datetime import datetime as dt
		try:
			return dt.strptime(date_str.strip(), "%d/%m/%Y").date()
		except Exception:
			pass
		try:
			return getdate(date_str)
		except Exception:
			pass
		try:
			return dt.strptime(date_str.strip(), "%d %b %Y").date()
		except Exception:
			return None

	def get_salik_income_account(self, company):
		"""Get income account for Salik charges"""
		# Try to get from settings or use default
		account = frappe.db.get_value("Salik Settings", "Salik Settings", "customer_charge_account")
		if account:
			return account
		# Fallback to default income account
		return frappe.db.get_value("Company", company, "default_income_account")

	def get_fines_income_account(self, company):
		"""Get income account for Traffic Fines"""
		# Try to get from settings or use default
		account = frappe.db.get_value("RTA Settings", "RTA Settings", "customer_charge_account")
		if account:
			return account
		# Fallback to default income account
		return frappe.db.get_value("Company", company, "default_income_account")

	def get_income_account(self, company):
		"""Get appropriate income account based on billing cycle"""
		from right_hire.setup.accounts import get_account

		account_map = {
			"Monthly": "Monthly Lease Revenue",
			"Quarterly": "Quarterly Lease Revenue",
			"Annual": "Annual Lease Revenue"
		}

		account_name = account_map.get(self.billing_cycle, "Monthly Lease Revenue")
		account = get_account(account_name, company, "Income Account")

		# Fallback to company default income account if not found
		if not account:
			account = frappe.db.get_value("Company", company, "default_income_account")

		return account

	def get_overage_account(self, company):
		"""Get KM overage income account"""
		from right_hire.setup.accounts import get_account
		account = get_account("KM Overage Charges", company, "Income Account")
		# Fallback to company default income account if not found
		if not account:
			account = frappe.db.get_value("Company", company, "default_income_account")
		return account

	def ensure_rental_service_item(self):
		"""Ensure Rental Service item exists"""
		if not frappe.db.exists("Item", "Rental Service"):
			try:
				item = frappe.new_doc("Item")
				item.item_code = "Rental Service"
				item.item_name = "Rental Service"
				item.item_group = "Services"
				item.stock_uom = "Nos"
				item.is_stock_item = 0
				item.is_sales_item = 1
				item.insert(ignore_permissions=True)
				frappe.db.commit()
			except Exception as e:
				frappe.log_error(f"Failed to create Rental Service item: {str(e)}")

	def update_vehicle_status(self, status):
		"""Update vehicle status"""
		if not self.vehicle:
			return
		try:
			frappe.db.set_value("Vehicle", self.vehicle, "status", status)
		except Exception as e:
			frappe.log_error(f"Failed to update vehicle status: {str(e)}")

	def cancel_pending_invoices(self):
		"""Cancel all pending scheduled invoices"""
		for line in self.invoice_schedule:
			if line.status == "Invoiced" and line.invoice_ref:
				# Cancel the Sales Invoice
				try:
					invoice = frappe.get_doc("Sales Invoice", line.invoice_ref)
					if invoice.docstatus == 1:
						invoice.cancel()
						line.status = "Pending"
						line.invoice_ref = None
				except Exception as e:
					frappe.log_error(f"Failed to cancel invoice {line.invoice_ref}: {str(e)}")

	@frappe.whitelist()
	def collect_advance_payment(self):
		"""Create Payment Entry for advance payment"""
		if not frappe.db.exists("DocType", "Payment Entry"):
			frappe.msgprint(_("ERPNext Payment Entry not available"))
			return

		if not self.advance_payment:
			frappe.throw(_("No advance payment amount specified"))

		# Create Payment Entry
		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Receive"
		pe.party_type = "Customer"
		pe.party = self.customer
		pe.paid_amount = flt(self.advance_payment)
		pe.received_amount = flt(self.advance_payment)
		pe.reference_no = self.name
		pe.reference_date = getdate()
		pe.remarks = f"Advance payment for Lease Contract {self.name} ({self.advance_months} months)"

		# Set custom fields
		pe.deposit_type = "Advance Payment"
		pe.vehicle = self.vehicle
		pe.lease_agreement = self.name

		# Get company and accounts
		company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

		pe.company = company
		pe.paid_from = self.get_customer_account(company)
		pe.paid_to = self.get_advance_account(company)

		pe.flags.ignore_mandatory = True
		pe.flags.ignore_validate = True
		pe.save(ignore_permissions=True)
		pe.submit()

		frappe.msgprint(_(f"Payment Entry {pe.name} created for advance payment"), indicator="green")
		return pe.name

	def get_customer_account(self, company):
		"""Get accounts receivable account"""
		from right_hire.setup.accounts import get_account
		return get_account("Debtors", company, "Receivable")

	def get_advance_account(self, company):
		"""Get advance payment liability account"""
		from right_hire.setup.accounts import get_account
		return get_account("Advance Lease Payments", company, "Current Liability")


@frappe.whitelist()
def generate_schedule(lease_agreement):
	"""Generate invoice schedule for a lease agreement (can be called before submit)"""
	doc = frappe.get_doc("Lease Agreement", lease_agreement)

	# Validate required fields
	if not doc.start_date:
		frappe.throw(_("Start Date is required"))
	if not doc.tenure_months or doc.tenure_months <= 0:
		frappe.throw(_("Tenure (Months) must be greater than 0"))
	if not doc.billing_cycle:
		frappe.throw(_("Billing Cycle is required"))
	if not doc.monthly_rate or doc.monthly_rate <= 0:
		frappe.throw(_("Monthly Rate must be greater than 0"))

	# Clear existing schedule
	doc.invoice_schedule = []

	# Call the generate method
	doc.generate_invoice_schedule()
	doc.save()

	return {
		"success": True,
		"count": len(doc.invoice_schedule)
	}


@frappe.whitelist()
def fix_missing_schedules():
	"""Fix invoice schedules for all submitted agreements with incomplete schedules"""
	fixed_count = 0
	errors = []

	# Get all submitted lease agreements
	agreements = frappe.get_all(
		"Lease Agreement",
		filters={"docstatus": 1, "lease_status": ["in", ["Active", "Draft"]]},
		fields=["name", "tenure_months", "start_date", "end_date", "monthly_rate", "billing_day"]
	)

	for agr in agreements:
		try:
			current_count = frappe.db.count("Lease Schedule Line", {"parent": agr.name})
			expected_count = agr.tenure_months + 1  # +1 for pro-rated first period

			# If schedule is incomplete (less than expected), regenerate
			if current_count < expected_count:
				# Get existing invoiced lines to preserve
				invoiced_lines = frappe.get_all(
					"Lease Schedule Line",
					filters={"parent": agr.name, "status": "Invoiced"},
					fields=["period_start", "period_end", "status", "invoice_ref", "invoice_date"]
				)

				# Delete existing schedule lines
				frappe.db.delete("Lease Schedule Line", {"parent": agr.name})

				# Generate new schedule lines directly in DB
				new_lines = _generate_schedule_lines(agr)

				# Insert new lines
				for idx, line in enumerate(new_lines, 1):
					# Check if this period was already invoiced
					for inv in invoiced_lines:
						if (getdate(line["period_start"]) == getdate(inv.period_start) and
							getdate(line["period_end"]) == getdate(inv.period_end)):
							line["status"] = inv.status
							line["invoice_ref"] = inv.invoice_ref
							line["invoice_date"] = inv.invoice_date
							break

					schedule_line = frappe.new_doc("Lease Schedule Line")
					schedule_line.parent = agr.name
					schedule_line.parenttype = "Lease Agreement"
					schedule_line.parentfield = "invoice_schedule"
					schedule_line.idx = idx
					schedule_line.period_start = line["period_start"]
					schedule_line.period_end = line["period_end"]
					schedule_line.invoice_date = line["invoice_date"]
					schedule_line.amount = line["amount"]
					schedule_line.status = line.get("status", "Pending")
					schedule_line.invoice_ref = line.get("invoice_ref")
					schedule_line.db_insert()

				fixed_count += 1
				frappe.logger().info(f"Fixed schedule for {agr.name}: {current_count} -> {len(new_lines)} lines")

		except Exception as e:
			errors.append(f"{agr.name}: {str(e)[:100]}")
			frappe.log_error(f"Failed to fix schedule for {agr.name}", "Fix Lease Schedules")

	frappe.db.commit()

	return {
		"fixed": fixed_count,
		"total": len(agreements),
		"errors": errors
	}


def _generate_schedule_lines(agr):
	"""Generate schedule lines for an agreement without saving"""
	lines = []
	billing_day = agr.billing_day or 1
	start_date = getdate(agr.start_date)
	end_date = getdate(agr.end_date)
	monthly_rate = flt(agr.monthly_rate)
	daily_rate = monthly_rate / 30

	# Calculate the first billing date after start_date
	first_billing_year = start_date.year
	first_billing_month = start_date.month
	max_day_in_start_month = calendar.monthrange(first_billing_year, first_billing_month)[1]
	actual_billing_day_in_start_month = min(billing_day, max_day_in_start_month)

	if start_date.day < actual_billing_day_in_start_month:
		first_billing_date = start_date.replace(day=actual_billing_day_in_start_month)
	else:
		next_month = add_months(start_date, 1)
		max_day_next = calendar.monthrange(next_month.year, next_month.month)[1]
		first_billing_date = next_month.replace(day=min(billing_day, max_day_next))

	# First invoice: Pro-rated period
	first_period_end = add_days(first_billing_date, -1)
	days_in_first_period = (first_period_end - start_date).days + 1
	first_amount = flt(daily_rate * days_in_first_period)

	lines.append({
		"period_start": start_date,
		"period_end": first_period_end,
		"invoice_date": add_days(first_period_end, 1),  # Invoice day after period ends
		"amount": round(first_amount, 2),
		"status": "Pending"
	})

	# Subsequent invoices: Full billing cycles
	current_billing_date = first_billing_date

	while current_billing_date <= end_date:
		period_start = current_billing_date
		next_billing = add_months(current_billing_date, 1)
		max_day_next = calendar.monthrange(next_billing.year, next_billing.month)[1]
		next_billing_date = next_billing.replace(day=min(billing_day, max_day_next))
		period_end = add_days(next_billing_date, -1)

		if period_start > end_date:
			break

		if period_end > end_date:
			period_end = end_date
			days_in_period = (period_end - period_start).days + 1
			amount = round(flt(daily_rate * days_in_period), 2)
		else:
			amount = monthly_rate

		lines.append({
			"period_start": period_start,
			"period_end": period_end,
			"invoice_date": add_days(period_end, 1),  # Invoice day after period ends
			"amount": amount,
			"status": "Pending"
		})

		current_billing_date = next_billing_date

	return lines


@frappe.whitelist()
def create_invoice_for_schedule(lease_agreement, schedule_line_name):
	"""Create invoice for a specific schedule line - called from UI button"""
	doc = frappe.get_doc("Lease Agreement", lease_agreement)

	# Find the schedule line
	schedule_line = None
	for line in doc.invoice_schedule:
		if line.name == schedule_line_name:
			schedule_line = line
			break

	if not schedule_line:
		frappe.throw(_("Schedule line not found"))

	if schedule_line.status != "Pending":
		frappe.throw(_("This period is already {0}").format(schedule_line.status))

	# Create the invoice
	invoice_name = doc.create_monthly_invoice(schedule_line)

	return {"invoice": invoice_name, "success": True}


@frappe.whitelist()
def generate_invoices_for_agreement(lease_agreement):
	"""Generate invoices for all pending due schedule lines for a specific agreement"""
	import traceback

	doc = frappe.get_doc("Lease Agreement", lease_agreement)
	today = getdate(nowdate())
	created = []
	errors = []

	for line in doc.invoice_schedule:
		# Check if period is due (period_start <= today) and not yet invoiced
		if line.status == "Pending" and getdate(line.period_start) <= today:
			try:
				invoice_name = doc.create_monthly_invoice(line)
				if invoice_name:
					created.append(invoice_name)
			except Exception as e:
				error_msg = f"Error creating invoice for period {line.period_start} to {line.period_end}: {str(e)}"
				errors.append(error_msg)
				frappe.log_error(
					f"{error_msg}\n{traceback.format_exc()}",
					"Lease Invoice Generation Error"
				)

	if errors:
		frappe.msgprint(
			_("Some invoices could not be created:<br>") + "<br>".join(errors),
			indicator="orange",
			title=_("Partial Success") if created else _("Error")
		)

	return {"created": created, "errors": errors}


@frappe.whitelist()
def create_due_invoices():
	"""Create invoices for all due periods across all active lease agreements"""
	import traceback
	created_count = 0
	errors = []
	today = getdate(nowdate())

	# Get all active lease agreements
	agreements = frappe.get_all(
		"Lease Agreement",
		filters={"docstatus": 1, "lease_status": "Active"},
		fields=["name"]
	)

	for agr in agreements:
		try:
			doc = frappe.get_doc("Lease Agreement", agr.name)

			for line in (doc.invoice_schedule or []):
				# Check if period is due (invoice_date <= today) and not yet invoiced
				if line.status == "Pending" and getdate(line.invoice_date) <= today:
					try:
						invoice_name = doc.create_monthly_invoice(line)
						if invoice_name:
							created_count += 1
							frappe.logger().info(f"Created invoice {invoice_name} for {agr.name}")
					except Exception as e:
						tb = traceback.format_exc()
						errors.append(f"{agr.name} - {line.period_start}: {str(e)}")
						frappe.log_error(f"Failed to create invoice for {agr.name}:\n{tb}", "Auto Invoice Creation")

		except Exception as e:
			errors.append(f"{agr.name}: {str(e)}")

	frappe.db.commit()

	return {
		"created": created_count,
		"agreements_processed": len(agreements),
		"errors": errors
	}


def auto_create_lease_invoices():
	"""Scheduled job to create due invoices - called daily"""
	result = create_due_invoices()
	if result.get("created", 0) > 0:
		frappe.logger().info(f"Auto-created {result['created']} lease invoices")
	if result.get("errors"):
		# Truncate error message to avoid CharacterLengthExceeded
		error_summary = str(result['errors'])[:500]
		frappe.log_error(f"Auto-invoice errors: {error_summary}", "Lease Auto Invoice")
	return result


@frappe.whitelist()
def create_salik_supplementary_invoice(lease_agreement):
	"""Create a supplementary invoice for unbilled Salik transactions.

	Use this to add Salik charges to a lease agreement when the regular
	invoice was already generated without them.
	"""
	from collections import defaultdict

	doc = frappe.get_doc("Lease Agreement", lease_agreement)

	if not doc.vehicle:
		frappe.throw(_("No vehicle linked to this lease agreement"))

	# Get all unbilled Salik transactions for this vehicle during the lease period
	salik_transactions = frappe.get_all(
		"Salik Transaction",
		filters={
			"vehicle": doc.vehicle,
			"transaction_date": ["between", [getdate(doc.start_date), getdate(doc.end_date)]],
			"charged_to_customer": 0
		},
		fields=["name", "transaction_date", "gate_location", "toll_amount", "toll_schedule"]
	)

	if not salik_transactions:
		frappe.msgprint(_("No unbilled Salik transactions found for this lease agreement"))
		return None

	# Salik markup percentage (10%)
	SALIK_MARKUP_PERCENT = 10
	SALIK_RATES = {
		"Peak": 6.00,
		"Low-Peak": 4.00,
		"Off-Peak": 0.00
	}

	# Group transactions by toll schedule
	grouped = defaultdict(lambda: {"count": 0, "transactions": []})
	for t in salik_transactions:
		schedule = t.get("toll_schedule") or "Peak"
		grouped[schedule]["count"] += 1
		grouped[schedule]["transactions"].append(t.name)

	# Get company
	company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

	# Create the invoice
	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = doc.customer
	invoice.posting_date = getdate()
	invoice.due_date = getdate()
	invoice.company = company
	invoice.currency = frappe.db.get_value("Company", company, "default_currency") or "AED"
	invoice.conversion_rate = 1.0
	invoice.selling_price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
	invoice.debit_to = frappe.db.get_value("Company", company, "default_receivable_account")

	# Set custom fields
	invoice.vehicle = doc.vehicle
	invoice.lease_agreement = doc.name

	income_account = doc.get_salik_income_account(company)

	schedule_order = ["Peak", "Low-Peak", "Off-Peak"]
	items_added = False

	for schedule in schedule_order:
		if schedule not in grouped:
			continue

		data = grouped[schedule]
		if data["count"] == 0:
			continue

		base_rate = SALIK_RATES.get(schedule, 4.00)

		# Skip Off-Peak (free) trips
		if base_rate == 0:
			for trans_name in data["transactions"]:
				frappe.db.set_value("Salik Transaction", trans_name, {
					"linked_contract": doc.name,
					"charged_to_customer": 1,
					"customer_charged_date": nowdate()
				}, update_modified=False)
			continue

		rate_with_markup = flt(base_rate * (1 + SALIK_MARKUP_PERCENT / 100), 2)
		amount = flt(rate_with_markup * data["count"], 2)

		invoice.append("items", {
			"item_code": "Rental Service",
			"item_name": f"Salik Toll - {schedule}",
			"description": f"Salik Toll - {schedule}",
			"qty": data["count"],
			"rate": rate_with_markup,
			"amount": amount,
			"income_account": income_account,
		})
		items_added = True

		# Mark transactions as invoiced
		for trans_name in data["transactions"]:
			frappe.db.set_value("Salik Transaction", trans_name, {
				"linked_contract": doc.name,
				"charged_to_customer": 1,
				"customer_charged_date": nowdate()
			}, update_modified=False)

	if not items_added:
		frappe.msgprint(_("No chargeable Salik transactions found (only Off-Peak which is free)"))
		return None

	# Save and submit
	invoice.save(ignore_permissions=True)
	invoice.submit()

	frappe.msgprint(_(f"Supplementary Salik Invoice {invoice.name} created with {len(salik_transactions)} transactions"), indicator="green")
	return invoice.name
