import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_accounting_custom_fields():
	"""Create custom fields for ERPNext accounting integration"""
	if not frappe.db.exists("DocType", "Sales Invoice"):
		frappe.logger().info("ERPNext not installed, skipping custom fields creation")
		return

	custom_fields = get_custom_fields_spec()

	try:
		create_custom_fields(custom_fields, ignore_validate=True, update=True)
		frappe.logger().info("Created accounting custom fields successfully")
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to create custom fields: {str(e)}", "Custom Fields Creation")

def get_custom_fields_spec():
	"""Get custom fields specification for ERPNext DocTypes"""
	return {
		"Sales Invoice": [
			# Rental/Lease Details Section
			{
				"fieldname": "rental_section",
				"label": "Rental/Lease Details",
				"fieldtype": "Section Break",
				"insert_after": "customer",
				"collapsible": 1
			},
			{
				"fieldname": "rental_type",
				"label": "Rental Type",
				"fieldtype": "Select",
				"options": "\nDaily Rental\nWeekly Rental\nMonthly Rental\nMonthly Lease\nQuarterly Lease\nAnnual Lease",
				"insert_after": "rental_section"
			},
			{
				"fieldname": "vehicle",
				"label": "Vehicle",
				"fieldtype": "Link",
				"options": "Vehicle",
				"insert_after": "rental_type"
			},
			{
				"fieldname": "rental_agreement",
				"label": "Rental Agreement",
				"fieldtype": "Link",
				"options": "Rental Agreement",
				"insert_after": "vehicle"
			},
			{
				"fieldname": "lease_contract",
				"label": "Lease Contract",
				"fieldtype": "Link",
				"options": "Lease Contract",
				"insert_after": "rental_agreement"
			},
			{
				"fieldname": "column_break_rental",
				"fieldtype": "Column Break",
				"insert_after": "lease_contract"
			},
			{
				"fieldname": "driver",
				"label": "Driver",
				"fieldtype": "Link",
				"options": "Driver",
				"insert_after": "column_break_rental"
			},
			# KM Details Section
			{
				"fieldname": "km_details_section",
				"label": "KM Details",
				"fieldtype": "Section Break",
				"insert_after": "driver",
				"collapsible": 1
			},
			{
				"fieldname": "odometer_out",
				"label": "Odometer Out",
				"fieldtype": "Int",
				"insert_after": "km_details_section"
			},
			{
				"fieldname": "odometer_in",
				"label": "Odometer In",
				"fieldtype": "Int",
				"insert_after": "odometer_out"
			},
			{
				"fieldname": "km_driven",
				"label": "KM Driven",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "odometer_in"
			},
			{
				"fieldname": "column_break_km",
				"fieldtype": "Column Break",
				"insert_after": "km_driven"
			},
			{
				"fieldname": "free_km",
				"label": "Free KM Allowance",
				"fieldtype": "Int",
				"insert_after": "column_break_km"
			},
			{
				"fieldname": "overage_km",
				"label": "Overage KM",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "free_km"
			},
			{
				"fieldname": "overage_rate",
				"label": "Overage Rate per KM",
				"fieldtype": "Currency",
				"insert_after": "overage_km"
			}
		],

		"Purchase Invoice": [
			# Vehicle Details Section
			{
				"fieldname": "vehicle_section",
				"label": "Vehicle Details",
				"fieldtype": "Section Break",
				"insert_after": "supplier",
				"collapsible": 1
			},
			{
				"fieldname": "vehicle",
				"label": "Vehicle",
				"fieldtype": "Link",
				"options": "Vehicle",
				"insert_after": "vehicle_section"
			},
			{
				"fieldname": "expense_type",
				"label": "Expense Type",
				"fieldtype": "Select",
				"options": "\nVehicle Purchase\nMaintenance\nFuel\nInsurance\nRegistration\nRepairs\nTires\nOther",
				"insert_after": "vehicle"
			},
			{
				"fieldname": "column_break_vehicle",
				"fieldtype": "Column Break",
				"insert_after": "expense_type"
			},
			{
				"fieldname": "maintenance_job",
				"label": "Maintenance Job",
				"fieldtype": "Link",
				"options": "Maintenance Job",
				"depends_on": "eval:doc.expense_type=='Maintenance'",
				"insert_after": "column_break_vehicle"
			},
			{
				"fieldname": "odometer_reading",
				"label": "Odometer Reading",
				"fieldtype": "Int",
				"insert_after": "maintenance_job"
			}
		],

		"Payment Entry": [
			# Rental/Lease Details Section
			{
				"fieldname": "rental_section",
				"label": "Rental/Lease Details",
				"fieldtype": "Section Break",
				"insert_after": "party",
				"collapsible": 1
			},
			{
				"fieldname": "deposit_type",
				"label": "Deposit Type",
				"fieldtype": "Select",
				"options": "\nSecurity Deposit\nAdvance Payment\nDeposit Refund",
				"insert_after": "rental_section"
			},
			{
				"fieldname": "vehicle",
				"label": "Vehicle",
				"fieldtype": "Link",
				"options": "Vehicle",
				"insert_after": "deposit_type"
			},
			{
				"fieldname": "column_break_rental_pe",
				"fieldtype": "Column Break",
				"insert_after": "vehicle"
			},
			{
				"fieldname": "rental_agreement",
				"label": "Rental Agreement",
				"fieldtype": "Link",
				"options": "Rental Agreement",
				"insert_after": "column_break_rental_pe"
			},
			{
				"fieldname": "lease_contract",
				"label": "Lease Contract",
				"fieldtype": "Link",
				"options": "Lease Contract",
				"insert_after": "rental_agreement"
			}
		]
	}
