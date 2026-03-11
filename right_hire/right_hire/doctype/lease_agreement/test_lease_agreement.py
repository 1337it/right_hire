# Copyright (c) 2024, Right Hire and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import getdate, add_months, nowdate, flt

class TestLeaseAgreement(unittest.TestCase):
	def setUp(self):
		"""Create test data"""
		self.create_test_customer()
		self.create_test_vehicle()
		self.create_test_branch()

	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()

	def create_test_customer(self):
		"""Create test customer"""
		if not frappe.db.exists("Customer", "Test Customer - Lease"):
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": "Test Customer - Lease",
				"customer_type": "Individual",
				"customer_group": "Individual",
				"territory": "All Territories"
			})
			customer.insert(ignore_permissions=True)

	def create_test_vehicle(self):
		"""Create test vehicle"""
		if not frappe.db.exists("Vehicle", "TEST-LEASE-001"):
			vehicle = frappe.get_doc({
				"doctype": "Vehicle",
				"vehicle_id": "TEST-LEASE-001",
				"plate_no": "TEST-LEASE-001",
				"make": "Toyota",
				"model": "Camry",
				"year": 2023,
				"vehicle_status": "Available",
				"branch": self.get_test_branch()
			})
			vehicle.insert(ignore_permissions=True)

	def create_test_branch(self):
		"""Create test branch"""
		if not frappe.db.exists("Branch", "Test Branch"):
			branch = frappe.get_doc({
				"doctype": "Branch",
				"branch_name": "Test Branch",
				"address": "Test Address"
			})
			branch.insert(ignore_permissions=True)

	def get_test_branch(self):
		"""Get test branch name"""
		if frappe.db.exists("Branch", "Test Branch"):
			return "Test Branch"
		elif frappe.db.exists("Branch", "Main Branch"):
			return "Main Branch"
		else:
			# Create a branch
			self.create_test_branch()
			return "Test Branch"

	def test_invoice_schedule_generation(self):
		"""Test monthly invoice schedule generation"""
		lease = frappe.get_doc({
			"doctype": "Lease Contract",
			"customer": "Test Customer - Lease",
			"vehicle": "TEST-LEASE-001",
			"start_date": getdate(),
			"end_date": add_months(getdate(), 12),
			"billing_cycle": "Monthly",
			"monthly_rate": 3000,
			"billing_day": 1,
			"branch": self.get_test_branch()
		})
		lease.insert(ignore_permissions=True)
		lease.submit()

		# Check schedule created
		self.assertEqual(len(lease.invoice_schedule), 12, "Should create 12 monthly invoice schedule lines")

		# Check first schedule line
		first_line = lease.invoice_schedule[0]
		self.assertEqual(first_line.status, "Pending", "First line should be Pending")
		self.assertEqual(flt(first_line.amount), 3000, "Amount should be 3000")

	def test_quarterly_invoice_schedule(self):
		"""Test quarterly invoice schedule generation"""
		lease = frappe.get_doc({
			"doctype": "Lease Contract",
			"customer": "Test Customer - Lease",
			"vehicle": "TEST-LEASE-001",
			"start_date": getdate(),
			"end_date": add_months(getdate(), 12),
			"billing_cycle": "Quarterly",
			"monthly_rate": 3000,
			"billing_day": 1,
			"branch": self.get_test_branch()
		})
		lease.insert(ignore_permissions=True)
		lease.submit()

		# Check schedule created (12 months / 3 = 4 quarters)
		self.assertEqual(len(lease.invoice_schedule), 4, "Should create 4 quarterly invoice schedule lines")

		# Check first schedule line amount (3 months * 3000)
		first_line = lease.invoice_schedule[0]
		self.assertEqual(flt(first_line.amount), 9000, "Quarterly amount should be 9000 (3 * 3000)")

	def test_invoice_creation(self):
		"""Test Sales Invoice creation from schedule"""
		if not frappe.db.exists("DocType", "Sales Invoice"):
			self.skipTest("ERPNext not installed")

		lease = frappe.get_doc({
			"doctype": "Lease Contract",
			"customer": "Test Customer - Lease",
			"vehicle": "TEST-LEASE-001",
			"start_date": getdate(),
			"end_date": add_months(getdate(), 6),
			"billing_cycle": "Monthly",
			"monthly_rate": 3000,
			"billing_day": 1,
			"branch": self.get_test_branch()
		})
		lease.insert(ignore_permissions=True)
		lease.submit()

		# Create invoice for first period
		schedule_line = lease.invoice_schedule[0]
		invoice_name = lease.create_monthly_invoice(schedule_line)

		# Verify invoice created
		self.assertTrue(frappe.db.exists("Sales Invoice", invoice_name), "Sales Invoice should be created")

		# Verify schedule updated
		lease.reload()
		self.assertEqual(lease.invoice_schedule[0].status, "Invoiced", "Schedule status should be Invoiced")
		self.assertEqual(lease.invoice_schedule[0].invoice_ref, invoice_name, "Invoice reference should be set")

		# Verify invoice details
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		self.assertEqual(invoice.customer, lease.customer, "Invoice customer should match lease customer")
		self.assertEqual(invoice.vehicle, lease.vehicle, "Invoice vehicle should match lease vehicle")
		self.assertEqual(invoice.lease_agreement, lease.name, "Invoice should reference lease contract")
		self.assertEqual(len(invoice.items), 1, "Invoice should have one item (lease rental)")
		self.assertEqual(flt(invoice.items[0].amount), 3000, "Invoice amount should match monthly rate")

	def test_tenure_calculation(self):
		"""Test automatic tenure calculation"""
		lease = frappe.get_doc({
			"doctype": "Lease Contract",
			"customer": "Test Customer - Lease",
			"vehicle": "TEST-LEASE-001",
			"start_date": getdate(),
			"end_date": add_months(getdate(), 12),
			"billing_cycle": "Monthly",
			"monthly_rate": 3000,
			"billing_day": 1,
			"branch": self.get_test_branch()
		})
		lease.insert(ignore_permissions=True)

		# Tenure should be calculated
		self.assertEqual(lease.tenure_months, 12, "Tenure should be 12 months")

	def test_vehicle_status_update(self):
		"""Test vehicle status update on lease submission"""
		lease = frappe.get_doc({
			"doctype": "Lease Contract",
			"customer": "Test Customer - Lease",
			"vehicle": "TEST-LEASE-001",
			"start_date": getdate(),
			"end_date": add_months(getdate(), 12),
			"billing_cycle": "Monthly",
			"monthly_rate": 3000,
			"billing_day": 1,
			"branch": self.get_test_branch()
		})
		lease.insert(ignore_permissions=True)
		lease.submit()

		# Check vehicle status updated
		vehicle = frappe.get_doc("Vehicle", "TEST-LEASE-001")
		self.assertEqual(vehicle.vehicle_status, "Leased", "Vehicle status should be Leased")

	def test_date_validation(self):
		"""Test start/end date validation"""
		with self.assertRaises(frappe.exceptions.ValidationError):
			lease = frappe.get_doc({
				"doctype": "Lease Contract",
				"customer": "Test Customer - Lease",
				"vehicle": "TEST-LEASE-001",
				"start_date": add_months(getdate(), 12),
				"end_date": getdate(),  # End before start
				"billing_cycle": "Monthly",
				"monthly_rate": 3000,
				"billing_day": 1,
				"branch": self.get_test_branch()
			})
			lease.insert(ignore_permissions=True)

	def test_payment_entry_creation(self):
		"""Test advance payment entry creation"""
		if not frappe.db.exists("DocType", "Payment Entry"):
			self.skipTest("ERPNext not installed")

		lease = frappe.get_doc({
			"doctype": "Lease Contract",
			"customer": "Test Customer - Lease",
			"vehicle": "TEST-LEASE-001",
			"start_date": getdate(),
			"end_date": add_months(getdate(), 12),
			"billing_cycle": "Monthly",
			"monthly_rate": 3000,
			"billing_day": 1,
			"advance_payment": 6000,
			"advance_months": 2,
			"branch": self.get_test_branch()
		})
		lease.insert(ignore_permissions=True)
		lease.submit()

		# Create advance payment
		pe_name = lease.collect_advance_payment()

		# Verify payment entry created
		self.assertTrue(frappe.db.exists("Payment Entry", pe_name), "Payment Entry should be created")

		# Verify payment details
		pe = frappe.get_doc("Payment Entry", pe_name)
		self.assertEqual(pe.payment_type, "Receive", "Payment type should be Receive")
		self.assertEqual(pe.party, lease.customer, "Party should be customer")
		self.assertEqual(flt(pe.paid_amount), 6000, "Amount should match advance payment")
		self.assertEqual(pe.deposit_type, "Advance Payment", "Deposit type should be Advance Payment")
