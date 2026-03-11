import frappe
from frappe.utils import getdate

def execute():
	"""Migrate existing data to ERPNext accounting"""

	# Check if ERPNext installed
	if not frappe.db.exists("DocType", "Sales Invoice"):
		print("ERPNext not installed, skipping migration")
		return

	frappe.logger().info("Starting ERPNext accounting migration...")

	# Step 1: Setup accounts
	print("\n1. Setting up Chart of Accounts...")
	setup_accounts()

	# Step 2: Create custom fields
	print("\n2. Creating custom fields...")
	create_custom_fields()

	# Step 3: Migrate existing Rental Agreements
	print("\n3. Migrating Rental Agreements...")
	migrate_rental_agreements()

	# Step 4: Migrate existing Lease Contracts
	print("\n4. Migrating Lease Contracts...")
	migrate_lease_contracts()

	# Step 5: Link existing maintenance jobs
	print("\n5. Linking Maintenance Jobs...")
	link_maintenance_jobs()

	# Step 6: Create Purchase Invoices for vehicles
	print("\n6. Creating Purchase Invoices for vehicles...")
	create_vehicle_purchase_invoices()

	frappe.logger().info("Migration completed successfully!")
	print("\n✓ Migration completed successfully!")

def setup_accounts():
	"""Setup Chart of Accounts and Cost Centers"""
	try:
		from right_hire.setup.accounts import create_rental_accounts, setup_default_accounts, setup_cost_centers

		company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

		if not company:
			print("  ⚠ No default company found, skipping account setup")
			return

		print(f"  Setting up accounts for company: {company}")
		create_rental_accounts(company)
		print("  ✓ Rental accounts created")

		setup_default_accounts(company)
		print("  ✓ Default accounts configured")

		setup_cost_centers(company)
		print("  ✓ Cost centers created")

		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to setup accounts: {str(e)}", "Account Setup Migration")
		print(f"  ✗ Error: {str(e)}")

def create_custom_fields():
	"""Create custom fields for ERPNext integration"""
	try:
		from right_hire.setup.custom_fields import create_accounting_custom_fields
		create_accounting_custom_fields()
		print("  ✓ Custom fields created")
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to create custom fields: {str(e)}", "Custom Fields Migration")
		print(f"  ✗ Error: {str(e)}")

def migrate_rental_agreements():
	"""Migrate existing rental agreements to create Sales Invoices"""
	agreements = frappe.get_all(
		"Rental Agreement",
		filters={"docstatus": 1, "erpnext_invoice": ["is", "not set"]},
		pluck="name"
	)

	print(f"  Found {len(agreements)} agreements to migrate")
	count = 0

	for agreement_name in agreements:
		try:
			agreement = frappe.get_doc("Rental Agreement", agreement_name)
			if not agreement.erpnext_invoice and agreement.agreement_status not in ["Draft", "Cancelled"]:
				agreement.create_erpnext_invoice()
				frappe.db.commit()
				count += 1
				print(f"  ✓ Created invoice for {agreement_name}")
		except Exception as e:
			frappe.log_error(f"Failed to migrate {agreement_name}: {str(e)}", "Rental Agreement Migration")
			print(f"  ✗ Failed: {agreement_name} - {str(e)}")
			frappe.db.rollback()

	print(f"  ✓ Migrated {count} rental agreements")

def migrate_lease_contracts():
	"""Generate invoice schedules for existing lease contracts"""
	leases = frappe.get_all(
		"Lease Contract",
		filters={"docstatus": 1, "lease_status": "Active"},
		pluck="name"
	)

	print(f"  Found {len(leases)} active leases to migrate")
	count = 0

	for lease_name in leases:
		try:
			lease = frappe.get_doc("Lease Contract", lease_name)
			if not lease.invoice_schedule:
				lease.generate_invoice_schedule()
				frappe.db.commit()
				count += 1
				print(f"  ✓ Generated schedule for {lease_name}")
		except Exception as e:
			frappe.log_error(f"Failed to migrate {lease_name}: {str(e)}", "Lease Contract Migration")
			print(f"  ✗ Failed: {lease_name} - {str(e)}")
			frappe.db.rollback()

	print(f"  ✓ Migrated {count} lease contracts")

def link_maintenance_jobs():
	"""Create Purchase Invoices for completed maintenance jobs"""
	jobs = frappe.get_all(
		"Maintenance Job",
		filters={
			"status": "Completed",
			"actual_cost": [">", 0],
			"docstatus": 1
		},
		pluck="name"
	)

	print(f"  Found {len(jobs)} completed maintenance jobs")
	count = 0

	for job_name in jobs:
		try:
			# Check if PI already exists
			existing = frappe.db.get_value(
				"Purchase Invoice",
				{"maintenance_job": job_name, "docstatus": 1},
				"name"
			)

			if not existing:
				job = frappe.get_doc("Maintenance Job", job_name)
				job.create_purchase_invoice()
				frappe.db.commit()
				count += 1
				print(f"  ✓ Created PI for maintenance job {job_name}")
		except Exception as e:
			frappe.log_error(f"Failed to create PI for {job_name}: {str(e)}", "Maintenance Job Migration")
			print(f"  ✗ Failed: {job_name} - {str(e)}")
			frappe.db.rollback()

	print(f"  ✓ Created Purchase Invoices for {count} maintenance jobs")

def create_vehicle_purchase_invoices():
	"""Create Purchase Invoices for vehicles with purchase cost"""
	vehicles = frappe.get_all(
		"Vehicle",
		filters={
			"purchase_cost": [">", 0],
			"purchase_date": ["is", "set"]
		},
		pluck="name"
	)

	print(f"  Found {len(vehicles)} vehicles with purchase information")
	count = 0

	for vehicle_name in vehicles:
		try:
			# Check if PI already exists
			existing = frappe.db.get_value(
				"Purchase Invoice",
				{"vehicle": vehicle_name, "expense_type": "Vehicle Purchase", "docstatus": 1},
				"name"
			)

			if not existing:
				vehicle = frappe.get_doc("Vehicle", vehicle_name)
				vehicle.create_purchase_invoice()
				frappe.db.commit()
				count += 1
				print(f"  ✓ Created PI for vehicle {vehicle_name}")
		except Exception as e:
			frappe.log_error(f"Failed to create PI for vehicle {vehicle_name}: {str(e)}", "Vehicle Purchase Migration")
			print(f"  ✗ Failed: {vehicle_name} - {str(e)}")
			frappe.db.rollback()

	print(f"  ✓ Created Purchase Invoices for {count} vehicles")
