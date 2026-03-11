# Copyright (c) 2024, Right Hire and contributors
# Vehicle Status setup with default statuses and transitions

import frappe
from frappe import _

def create_default_vehicle_statuses():
	"""Create default vehicle statuses with allowed transitions"""

	# Define statuses with their properties
	statuses = [
		{
			"status_name": "Available",
			"display_order": 1,
			"color": "green",
			"is_terminal": 0,
			"is_available_for_booking": 1,
			"description": "Vehicle is available for booking",
			"transitions": ["Reserved", "Out for Delivery", "Rented Out", "Leased", "At Garage", "Under Maintenance", "Deactivated"]
		},
		{
			"status_name": "Reserved",
			"display_order": 2,
			"color": "blue",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is reserved for a customer",
			"transitions": ["Available", "Out for Delivery", "Rented Out"]
		},
		{
			"status_name": "Out for Delivery",
			"display_order": 3,
			"color": "purple",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is being delivered to customer",
			"transitions": ["Rented Out", "Leased", "Available"]
		},
		{
			"status_name": "Rented Out",
			"display_order": 4,
			"color": "orange",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is currently on rent",
			"transitions": ["Due for Return", "Custody", "Accident/Repair"]
		},
		{
			"status_name": "Leased",
			"display_order": 5,
			"color": "orange",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is on long-term lease",
			"transitions": ["Due for Return", "Custody", "Accident/Repair"]
		},
		{
			"status_name": "Due for Return",
			"display_order": 6,
			"color": "yellow",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is due for return from customer",
			"transitions": ["Available", "At Garage", "Custody"]
		},
		{
			"status_name": "Custody",
			"display_order": 7,
			"color": "gray",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is in custody (police, authorities, etc.)",
			"transitions": ["Available", "At Garage", "Accident/Repair", "Deactivated"]
		},
		{
			"status_name": "At Garage",
			"display_order": 8,
			"color": "red",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is at garage for cleaning/minor work",
			"transitions": ["Available", "Under Maintenance"]
		},
		{
			"status_name": "Under Maintenance",
			"display_order": 9,
			"color": "red",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is under scheduled maintenance",
			"transitions": ["Available", "At Garage"]
		},
		{
			"status_name": "Accident/Repair",
			"display_order": 10,
			"color": "red",
			"is_terminal": 0,
			"is_available_for_booking": 0,
			"description": "Vehicle is being repaired after accident",
			"transitions": ["Available", "Under Maintenance", "Deactivated"]
		},
		{
			"status_name": "Deactivated",
			"display_order": 11,
			"color": "gray",
			"is_terminal": 1,
			"is_available_for_booking": 0,
			"description": "Vehicle is deactivated/sold/disposed",
			"transitions": []
		}
	]

	# First pass: Create all statuses without transitions
	for status_data in statuses:
		transitions = status_data.pop("transitions", [])
		status_data["_transitions"] = transitions  # Store for later

		if not frappe.db.exists("Vehicle Status", status_data["status_name"]):
			doc = frappe.new_doc("Vehicle Status")
			for key, value in status_data.items():
				if not key.startswith("_"):
					setattr(doc, key, value)
			doc.flags.ignore_links = True
			doc.insert(ignore_permissions=True)
			print(f"Created status: {status_data['status_name']}")
		else:
			print(f"Status already exists: {status_data['status_name']}")

	frappe.db.commit()

	# Second pass: Add transitions
	for status_data in statuses:
		transitions = status_data.get("_transitions", [])
		if not transitions:
			continue

		doc = frappe.get_doc("Vehicle Status", status_data["status_name"])
		doc.allowed_transitions = []

		for target_status in transitions:
			if frappe.db.exists("Vehicle Status", target_status):
				doc.append("allowed_transitions", {
					"target_status": target_status,
					"requires_reason": 1 if target_status in ["Deactivated", "Custody", "Accident/Repair"] else 0,
					"allowed_roles": "LeetRental Admin" if target_status == "Deactivated" else ""
				})

		doc.save(ignore_permissions=True)
		print(f"Added {len(doc.allowed_transitions)} transitions to {status_data['status_name']}")

	frappe.db.commit()
	print("Default Vehicle Statuses created successfully")


def execute():
	"""Run during app setup/migration"""
	create_default_vehicle_statuses()
