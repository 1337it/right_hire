# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

"""
RTA Vehicle Sync Integration
Syncs vehicle data from RTA API including registration card images
"""

import frappe
import requests
import base64
import json
from frappe.utils import now_datetime
from datetime import datetime


@frappe.whitelist()
def sync_vehicles_from_rta():
	"""
	Sync vehicles from RTA API
	- Updates existing vehicles with registration images
	- Creates draft vehicles for new vehicles not in the system
	"""
	settings = frappe.get_cached_doc("RTA Settings")

	if not settings.enabled:
		return {"status": "error", "message": "RTA integration is disabled"}

	api_base_url = settings.api_base_url
	api_key = settings.get_password("api_key")

	if not api_base_url or not api_key:
		return {"status": "error", "message": "RTA API not configured"}

	try:
		# Fetch vehicles from API
		# Remove trailing slash from base URL if present
		api_base_url = api_base_url.rstrip("/")
		response = requests.get(
			f"{api_base_url}/vehicles",
			headers={"X-API-Key": api_key},
			timeout=60
		)
		response.raise_for_status()
		data = response.json()

		vehicles = data.get("vehicles", [])
		total = data.get("total", 0)

		synced = 0
		created = 0
		errors = []

		for vehicle_data in vehicles:
			try:
				result = process_vehicle(vehicle_data)
				if result == "synced":
					synced += 1
				elif result == "created":
					created += 1
			except Exception as e:
				errors.append(f"{vehicle_data.get('plate_number')}: {str(e)}")
				frappe.log_error(
					f"Error processing vehicle {vehicle_data.get('plate_number')}: {str(e)}",
					"RTA Vehicle Sync Error"
				)

		frappe.db.commit()

		# Update sync status
		update_sync_status(total, synced, created, errors)

		return {
			"status": "success",
			"total_from_api": total,
			"synced": synced,
			"created": created,
			"errors": len(errors)
		}

	except requests.RequestException as e:
		error_msg = f"API request failed: {str(e)}"
		frappe.log_error(error_msg, "RTA Vehicle Sync Error")
		return {"status": "error", "message": error_msg}


def process_vehicle(vehicle_data):
	"""Process a single vehicle from API data"""
	plate_number = vehicle_data.get("plate_number")
	plate_code = vehicle_data.get("plate_code", "")
	plate_type = vehicle_data.get("plate_type", "")
	rta_vehicle_id = vehicle_data.get("id")
	status = vehicle_data.get("status")
	plate_category = vehicle_data.get("plate_category")

	# Parse raw_data for images
	raw_data = vehicle_data.get("raw_data", "{}")
	if isinstance(raw_data, str):
		raw_data = json.loads(raw_data)
	images = raw_data.get("images", [])

	# Build full plate number for matching (e.g., "49962 FF" or just "49962")
	# Try different matching strategies
	existing_vehicle = find_existing_vehicle(plate_number, plate_code, plate_type)

	if existing_vehicle:
		# Update existing vehicle
		update_vehicle_rta_data(existing_vehicle, rta_vehicle_id, status, plate_category, images)
		return "synced"
	else:
		# Create new draft vehicle
		create_draft_vehicle(vehicle_data, images)
		return "created"


def find_existing_vehicle(plate_number, plate_code, plate_type):
	"""Find existing vehicle by plate number"""
	# Try exact match first
	vehicle = frappe.db.get_value("Vehicle", {"plate_no": plate_number}, "name")
	if vehicle:
		return vehicle

	# Try with plate type suffix (e.g., "49962 FF")
	plate_with_type = f"{plate_number} {plate_type}".strip()
	vehicle = frappe.db.get_value("Vehicle", {"plate_no": plate_with_type}, "name")
	if vehicle:
		return vehicle

	# Try searching in plate_no field with LIKE
	vehicle = frappe.db.get_value(
		"Vehicle",
		{"plate_no": ["like", f"%{plate_number}%"]},
		"name"
	)
	return vehicle


def update_vehicle_rta_data(vehicle_name, rta_vehicle_id, status, plate_category, images):
	"""Update vehicle with RTA data and registration images (only if missing)"""
	# Update scalar fields directly without loading the full doc
	frappe.db.set_value("Vehicle", vehicle_name, {
		"rta_vehicle_id": rta_vehicle_id,
		"rta_registration_status": status,
		"rta_plate_category": plate_category,
		"rta_last_sync": now_datetime()
	}, update_modified=False)

	# Only save registration images if the vehicle doesn't already have them
	current_front = frappe.db.get_value("Vehicle", vehicle_name, "rta_registration_front")
	current_back = frappe.db.get_value("Vehicle", vehicle_name, "rta_registration_back")

	if not current_front and len(images) >= 1 and images[0].get("image"):
		front_file = save_base64_image(
			images[0]["image"],
			f"reg_front_{vehicle_name}.jpg",
			"Vehicle",
			vehicle_name
		)
		if front_file:
			frappe.db.set_value("Vehicle", vehicle_name, "rta_registration_front", front_file, update_modified=False)

	if not current_back and len(images) >= 2 and images[1].get("image"):
		back_file = save_base64_image(
			images[1]["image"],
			f"reg_back_{vehicle_name}.jpg",
			"Vehicle",
			vehicle_name
		)
		if back_file:
			frappe.db.set_value("Vehicle", vehicle_name, "rta_registration_back", back_file, update_modified=False)


def create_draft_vehicle(vehicle_data, images):
	"""Create a new draft vehicle from RTA data"""
	plate_number = vehicle_data.get("plate_number")
	plate_type = vehicle_data.get("plate_type", "")
	plate_code = vehicle_data.get("plate_code", "")

	# Create full plate number
	full_plate = f"{plate_number} {plate_type}".strip() if plate_type else plate_number

	vehicle = frappe.new_doc("Vehicle")
	vehicle.plate_no = full_plate
	vehicle.rta_vehicle_id = vehicle_data.get("id")
	vehicle.rta_registration_status = vehicle_data.get("status")
	vehicle.rta_plate_category = vehicle_data.get("plate_category")
	vehicle.rta_last_sync = now_datetime()

	# Set default status
	vehicle.status = "Available"

	# Try to extract expiry date from description
	description = vehicle_data.get("description", "")
	if "Expiry Date" in description:
		try:
			# Format: "Expiry Date : 01/08/2027"
			import re
			match = re.search(r"Expiry Date\s*:\s*(\d{2}/\d{2}/\d{4})", description)
			if match:
				expiry_str = match.group(1)
				expiry_date = datetime.strptime(expiry_str, "%d/%m/%Y").date()
				vehicle.registration_expiry = expiry_date
		except Exception:
			pass

	vehicle.insert(ignore_permissions=True)

	# Save registration images after insert (need the name)
	if len(images) >= 1 and images[0].get("image"):
		front_file = save_base64_image(
			images[0]["image"],
			f"reg_front_{vehicle.name}.jpg",
			"Vehicle",
			vehicle.name
		)
		if front_file:
			vehicle.rta_registration_front = front_file

	if len(images) >= 2 and images[1].get("image"):
		back_file = save_base64_image(
			images[1]["image"],
			f"reg_back_{vehicle.name}.jpg",
			"Vehicle",
			vehicle.name
		)
		if back_file:
			vehicle.rta_registration_back = back_file

	if vehicle.rta_registration_front or vehicle.rta_registration_back:
		vehicle.save(ignore_permissions=True)

	frappe.msgprint(
		f"New vehicle draft created: {vehicle.name} (Plate: {full_plate})",
		alert=True
	)


def save_base64_image(base64_data, filename, doctype, docname):
	"""Save base64 image as a file and return the file URL"""
	try:
		# Decode base64
		image_data = base64.b64decode(base64_data)

		# Create file
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": filename,
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
			"is_private": 1,
			"content": image_data
		})
		file_doc.save(ignore_permissions=True)

		return file_doc.file_url

	except Exception as e:
		frappe.log_error(
			f"Failed to save image {filename}: {str(e)}",
			"RTA Vehicle Sync - Image Save Error"
		)
		return None


def update_sync_status(total, synced, created, errors):
	"""Update RTA Settings with sync status"""
	try:
		frappe.db.set_value(
			"RTA Settings",
			"RTA Settings",
			{
				"last_successful_sync": now_datetime(),
				"total_vehicles_synced": synced + created
			},
			update_modified=False
		)
	except Exception:
		pass
