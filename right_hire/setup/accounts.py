import frappe
from frappe import _
from frappe.utils import cint

def create_rental_accounts(company):
	"""Create car rental specific Chart of Accounts"""
	if not company:
		frappe.throw(_("Company is required"))

	frappe.logger().info(f"Creating rental accounts for company: {company}")

	# Get company currency
	company_currency = frappe.db.get_value("Company", company, "default_currency") or "AED"

	# Account structure for car rental business
	rental_accounts = {
		"Income": {
			"Direct Income": {
				"Rental Revenue": {
					"Daily Rentals": {"account_type": "Income Account"},
					"Weekly Rentals": {"account_type": "Income Account"},
					"Monthly Rentals": {"account_type": "Income Account"},
					"Monthly Lease Revenue": {"account_type": "Income Account"},
					"Quarterly Lease Revenue": {"account_type": "Income Account"},
					"Annual Lease Revenue": {"account_type": "Income Account"},
				},
				"Other Rental Income": {
					"KM Overage Charges": {"account_type": "Income Account"},
					"Late Return Fees": {"account_type": "Income Account"},
					"Damage Charges": {"account_type": "Income Account"},
					"Fuel Charges": {"account_type": "Income Account"},
					"Additional Driver Charges": {"account_type": "Income Account"},
				}
			}
		},
		"Expenses": {
			"Direct Expenses": {
				"Vehicle Operating Expenses": {
					"Fuel Expenses": {"account_type": "Expense Account"},
					"Vehicle Maintenance": {"account_type": "Expense Account"},
					"Vehicle Repairs": {"account_type": "Expense Account"},
					"Tire Replacement": {"account_type": "Expense Account"},
					"Oil Changes": {"account_type": "Expense Account"},
				},
				"Vehicle Insurance": {
					"Comprehensive Insurance": {"account_type": "Expense Account"},
					"Third Party Insurance": {"account_type": "Expense Account"},
				},
				"Vehicle Registration": {
					"Registration Fees": {"account_type": "Expense Account"},
					"License Renewal": {"account_type": "Expense Account"},
				},
				"Depreciation": {
					"Vehicle Depreciation": {"account_type": "Depreciation"}
				}
			}
		},
		"Assets": {
			"Fixed Assets": {
				"Vehicles": {
					"Rental Fleet - Sedans": {"account_type": "Fixed Asset", "is_group": 0},
					"Rental Fleet - SUVs": {"account_type": "Fixed Asset", "is_group": 0},
					"Rental Fleet - Luxury": {"account_type": "Fixed Asset", "is_group": 0},
					"Rental Fleet - Commercial": {"account_type": "Fixed Asset", "is_group": 0},
					"Accumulated Depreciation - Vehicles": {
						"account_type": "Accumulated Depreciation",
						"is_group": 0
					}
				}
			},
			"Current Assets": {
				"Customer Deposits Held": {
					"Rental Security Deposits": {"account_type": "Current Asset"},
					"Lease Security Deposits": {"account_type": "Current Asset"},
				}
			}
		},
		"Liabilities": {
			"Current Liabilities": {
				"Customer Deposit Liabilities": {
					"Rental Deposits Payable": {"account_type": "Current Liability"},
					"Lease Deposits Payable": {"account_type": "Current Liability"},
				},
				"Advance Payments": {
					"Advance Lease Payments": {"account_type": "Current Liability"}
				}
			}
		}
	}

	# Create accounts recursively
	for root_type, root_accounts in rental_accounts.items():
		# Get root account for this type
		root_account = frappe.db.get_value(
			"Account",
			{"company": company, "root_type": root_type, "is_group": 1},
			"name"
		)

		if not root_account:
			frappe.logger().warn(f"Root account for {root_type} not found for company {company}")
			continue

		_create_accounts_recursive(root_accounts, root_account, company, company_currency, root_type)

	frappe.db.commit()
	frappe.logger().info(f"Rental accounts created successfully for {company}")

def _create_accounts_recursive(account_dict, parent_account, company, currency, root_type, level=0):
	"""Recursively create account hierarchy"""
	for account_name, account_data in account_dict.items():
		# Check if account already exists
		existing_account = frappe.db.get_value(
			"Account",
			{"account_name": account_name, "company": company},
			"name"
		)

		if existing_account:
			frappe.logger().debug(f"Account {account_name} already exists, skipping")
			current_account = existing_account
		else:
			# Determine if this is a group account (has children)
			is_group = 1 if any(isinstance(v, dict) for v in account_data.values() if not isinstance(v, str) and v != 0) else 0

			# Extract account type
			account_type = account_data.get("account_type", None)

			# Override is_group if explicitly set
			if "is_group" in account_data:
				is_group = account_data["is_group"]

			# Create account
			account = frappe.get_doc({
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent_account,
				"company": company,
				"is_group": is_group,
				"root_type": root_type,
				"account_type": account_type if account_type else None,
				"account_currency": currency
			})

			try:
				account.insert(ignore_permissions=True)
				frappe.logger().info(f"{'  ' * level}Created account: {account_name} (Group: {is_group}, Type: {account_type})")
				current_account = account.name
			except Exception as e:
				frappe.log_error(f"Failed to create account {account_name}: {str(e)}")
				continue

		# Recursively create child accounts
		for key, value in account_data.items():
			if isinstance(value, dict) and key not in ["account_type", "is_group"]:
				_create_accounts_recursive({key: value}, current_account, company, currency, root_type, level + 1)

def setup_default_accounts(company):
	"""Configure default accounts for company"""
	if not company:
		return

	frappe.logger().info(f"Setting up default accounts for {company}")

	# Get default income account
	default_income_account = frappe.db.get_value(
		"Account",
		{"account_name": "Daily Rentals", "company": company},
		"name"
	)

	# Get default expense account
	default_expense_account = frappe.db.get_value(
		"Account",
		{"account_name": "Vehicle Maintenance", "company": company},
		"name"
	)

	# Update company defaults if accounts exist
	company_doc = frappe.get_doc("Company", company)

	if default_income_account and not company_doc.get("default_income_account"):
		company_doc.db_set("default_income_account", default_income_account, update_modified=False)
		frappe.logger().info(f"Set default income account: {default_income_account}")

	if default_expense_account and not company_doc.get("default_expense_account"):
		company_doc.db_set("default_expense_account", default_expense_account, update_modified=False)
		frappe.logger().info(f"Set default expense account: {default_expense_account}")

	frappe.db.commit()

def setup_cost_centers(company=None):
	"""Create Cost Centers for each Branch"""
	if not company:
		company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

	if not company:
		frappe.logger().warn("No default company found, skipping cost center setup")
		return

	frappe.logger().info(f"Setting up cost centers for {company}")

	# Get all branches
	branches = frappe.get_all("Branch", fields=["name", "branch_name", "cost_center"])

	# Get root cost center for company
	root_cost_center = frappe.db.get_value(
		"Cost Center",
		{"company": company, "is_group": 1, "parent_cost_center": ["is", "not set"]},
		"name"
	)

	if not root_cost_center:
		frappe.logger().warn(f"Root cost center not found for company {company}")
		return

	for branch in branches:
		# Skip if cost center already set
		if branch.get("cost_center"):
			frappe.logger().debug(f"Branch {branch.branch_name} already has cost center")
			continue

		# Check if cost center exists
		cost_center_name = f"{branch.branch_name} - {company}"
		existing_cc = frappe.db.get_value("Cost Center", {"cost_center_name": branch.branch_name, "company": company}, "name")

		if existing_cc:
			cost_center = existing_cc
			frappe.logger().debug(f"Cost center {cost_center_name} already exists")
		else:
			# Create cost center
			cc = frappe.get_doc({
				"doctype": "Cost Center",
				"cost_center_name": branch.branch_name,
				"parent_cost_center": root_cost_center,
				"company": company,
				"is_group": 0
			})

			try:
				cc.insert(ignore_permissions=True)
				cost_center = cc.name
				frappe.logger().info(f"Created cost center: {cost_center_name}")
			except Exception as e:
				frappe.log_error(f"Failed to create cost center for branch {branch.branch_name}: {str(e)}")
				continue

		# Link cost center to branch
		try:
			frappe.db.set_value("Branch", branch.name, "cost_center", cost_center, update_modified=False)
			frappe.logger().info(f"Linked cost center {cost_center} to branch {branch.branch_name}")
		except Exception as e:
			frappe.log_error(f"Failed to link cost center to branch {branch.branch_name}: {str(e)}")

	frappe.db.commit()

def get_account(account_name, company, account_type=None):
	"""Get account by name, with fallback to account type"""
	# Try to get by account name
	account = frappe.db.get_value(
		"Account",
		{"account_name": account_name, "company": company},
		"name"
	)

	if account:
		return account

	# Fallback to account type if provided
	if account_type:
		account = frappe.db.get_value(
			"Account",
			{"account_type": account_type, "company": company, "is_group": 0},
			"name",
			order_by="creation"
		)

		if account:
			frappe.logger().warn(f"Account {account_name} not found, using fallback account type {account_type}: {account}")
			return account

	# If still not found, log warning but don't fail
	frappe.logger().warn(f"Account {account_name} not found for company {company}")
	return None
