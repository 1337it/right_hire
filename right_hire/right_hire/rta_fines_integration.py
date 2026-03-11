"""
RTA Traffic Fines Integration Module
Integrates with RTA Traffic Fines API to fetch and sync traffic fines
"""

import frappe
import requests
import time
import json
from datetime import datetime, timedelta

class RTAFinesAPI:
	"""RTA Traffic Fines API client"""

	def __init__(self):
		self.settings = frappe.get_single("RTA Settings")
		if not self.settings.enabled:
			frappe.throw("RTA Integration is disabled")

		self.base_url = self.settings.api_base_url or "http://139.185.53.79:8000/api"
		self.api_key = self.settings.get_password("api_key")

		if not self.api_key:
			frappe.throw("API Key not configured in RTA Settings")

		self.headers = {
			"X-API-Key": self.api_key,
			"Content-Type": "application/json"
		}

	def trigger_scraping(self, plate_source, plate_category, plate_code, plate_number):
		"""Trigger RTA fines scraping for a vehicle"""
		url = f"{self.base_url}/scrape/rta-fines"

		payload = {
			"plate_source": plate_source,
			"plate_category": plate_category or "Private",
			"plate_code": plate_code,
			"plate_number": plate_number
		}

		frappe.logger().info(f"Triggering RTA fines scraping for {plate_source} {plate_code} {plate_number}")

		try:
			response = requests.post(url, json=payload, headers=self.headers, timeout=30)
			response.raise_for_status()
			result = response.json()

			frappe.logger().info(f"Scraping job started: {result.get('job_id')}")
			return result
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="RTA Fines API", message=f"Failed to trigger scraping: {str(e)}")
			return None

	def check_job_status(self, job_id):
		"""Check the status of a scraping job"""
		url = f"{self.base_url}/status/{job_id}"

		try:
			response = requests.get(url, headers=self.headers, timeout=30)
			response.raise_for_status()
			return response.json()
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="RTA Fines API", message=f"Failed to check job status: {str(e)}")
			return None

	def get_fines(self, plate_source=None, plate_number=None, limit=100, offset=0, include_paid=False):
		"""Retrieve fines from the API"""
		url = f"{self.base_url}/fines"

		params = {"limit": limit, "offset": offset}
		if include_paid:
			params["include_paid"] = "true"
		if plate_source:
			params["plate_source"] = plate_source
		if plate_number:
			params["plate_number"] = plate_number

		try:
			response = requests.get(url, params=params, headers=self.headers, timeout=30)
			response.raise_for_status()
			return response.json()
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="RTA Fines API", message=f"Failed to retrieve fines: {str(e)}")
			return None

	def get_fine_by_id(self, fine_id):
		"""Get a specific fine by its API ID"""
		url = f"{self.base_url}/fines/{fine_id}"

		try:
			response = requests.get(url, headers=self.headers, timeout=30)
			response.raise_for_status()
			return response.json()
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="RTA Fines API", message=f"Failed to retrieve fine {fine_id}: {str(e)}")
			return None


@frappe.whitelist()
def sync_vehicle_fines(vehicle):
	"""Sync traffic fines for a specific vehicle"""
	try:
		vehicle_doc = frappe.get_doc("Vehicle", vehicle)

		if not vehicle_doc.rta_sync_enabled:
			return {"status": "disabled", "message": "RTA sync is disabled for this vehicle"}

		# Validate required plate fields
		if not vehicle_doc.plate_source or not vehicle_doc.plate_code or not vehicle_doc.plate_no:
			return {"status": "error", "message": "Vehicle missing required plate information"}

		api = RTAFinesAPI()

		# Get or create API Status record
		api_status_name = "RTA Traffic Fines"
		if not frappe.db.exists("API Status", api_status_name):
			api_status = frappe.new_doc("API Status")
			api_status.api_name = api_status_name
			api_status.api_type = "RTA Traffic Fines"
			api_status.insert(ignore_permissions=True)
		else:
			api_status = frappe.get_doc("API Status", api_status_name)

		# Trigger scraping
		result = api.trigger_scraping(
			plate_source=vehicle_doc.plate_source,
			plate_category=vehicle_doc.plate_category or "Private",
			plate_code=vehicle_doc.plate_code,
			plate_number=vehicle_doc.plate_no
		)

		if not result or not result.get("job_id"):
			api_status.update_status("Failed", error_message="Failed to trigger scraping")
			return {"status": "error", "message": "Failed to trigger scraping"}

		job_id = result["job_id"]
		api_status.mark_started(job_id)

		# Wait for job to complete (with timeout)
		max_wait_time = 300  # 5 minutes
		wait_interval = 10  # 10 seconds
		elapsed_time = 0

		while elapsed_time < max_wait_time:
			status_result = api.check_job_status(job_id)

			if not status_result:
				break

			status = status_result.get("status")
			frappe.logger().info(f"Job {job_id} status: {status}")

			if status == "completed":
				# Job completed, fetch the fines
				fines_data = api.get_fines(
					plate_source=vehicle_doc.plate_source,
					plate_number=vehicle_doc.plate_no
				)

				if fines_data and fines_data.get("fines"):
					new_count = save_fines_to_doctype(fines_data["fines"], vehicle_doc.name)

					api_status.update_status(
						"Success",
						job_id=job_id,
						records_fetched=new_count
					)

					return {
						"status": "success",
						"job_id": job_id,
						"total_fines": fines_data.get("total", 0),
						"new_fines": new_count
					}
				else:
					api_status.update_status("Success", job_id=job_id, records_fetched=0)
					return {
						"status": "success",
						"job_id": job_id,
						"message": "No fines found"
					}

			elif status == "failed":
				error_msg = status_result.get("error_message", "Unknown error")
				api_status.update_status("Failed", job_id=job_id, error_message=error_msg)
				return {"status": "error", "message": error_msg}

			# Wait before checking again
			time.sleep(wait_interval)
			elapsed_time += wait_interval

		# Timeout
		api_status.update_status("Failed", job_id=job_id, error_message="Scraping timeout")
		return {"status": "error", "message": "Scraping timeout"}

	except Exception as e:
		frappe.log_error(title="RTA Fines Sync", message=f"Error syncing vehicle fines: {str(e)}")
		return {"status": "error", "message": str(e)}


def _parse_fine_date_to_date(fine_date_str):
	"""Parse fine_date string (DD/MM/YYYY) to a date object."""
	if not fine_date_str:
		return None
	for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
		try:
			return datetime.strptime(fine_date_str, fmt).date()
		except (ValueError, TypeError):
			continue
	return None


def _find_agreement_for_vehicle(vehicle_name, fine_date):
	"""Find the active lease or rental agreement for a vehicle on a given date."""
	if not vehicle_name or not fine_date:
		return None, None, None

	# Check Lease Agreement first
	lease = frappe.db.get_value(
		"Lease Agreement",
		filters={
			"vehicle": vehicle_name,
			"docstatus": 1,
			"start_date": ["<=", fine_date],
			"end_date": [">=", fine_date],
		},
		fieldname=["name", "customer"],
		as_dict=True,
		order_by="creation desc"
	)
	if lease:
		return "lease", lease.name, lease.customer

	# Check Rental Agreement
	rental = frappe.db.get_value(
		"Rental Agreement",
		filters={
			"vehicle": vehicle_name,
			"docstatus": 1,
			"start_datetime": ["<=", fine_date],
			"end_datetime": [">=", fine_date],
		},
		fieldname=["name", "customer"],
		as_dict=True,
		order_by="creation desc"
	)
	if rental:
		return "rental", rental.name, rental.customer

	return None, None, None


def save_fines_to_doctype(fines, vehicle=None):
	"""Save fines to Traffic Fine DocType.

	If vehicle is not specified, attempts to match via plate_no.
	Links fines to the active agreement for the vehicle on the fine date.
	"""
	new_count = 0

	for fine in fines:
		try:
			fine_number = fine.get("fine_number")
			is_paid_to_rta = 1 if fine.get("paid") else 0

			# Check if fine already exists
			existing = frappe.db.exists("Traffic Fine", {"fine_number": fine_number})

			if existing:
				# Update paid and charged_to_customer status if changed
				current = frappe.db.get_value(
					"Traffic Fine", {"fine_number": fine_number},
					["name", "paid", "charged_to_customer", "ticket_id", "ticket_photo"], as_dict=True
				)
				updates = {}
				if current.paid != is_paid_to_rta:
					updates["paid"] = is_paid_to_rta
				# If paid to RTA, mark as charged to customer (no invoice needed)
				if is_paid_to_rta and not current.charged_to_customer:
					updates["charged_to_customer"] = 1

				# Update new fields if not yet populated
				if not current.ticket_id and fine.get("ticket_id"):
					updates["ticket_id"] = fine.get("ticket_id")
					updates["traffic_fine_id"] = fine.get("traffic_fine_id")
					updates["ticket_type"] = fine.get("ticket_type")
					updates["chassis_no"] = fine.get("chassis_no")
					updates["vehicle_id"] = fine.get("vehicle_id")
					updates["traffic_file_id"] = fine.get("traffic_file_id")
					updates["dispute_url"] = fine.get("dispute_url")
					updates["dispute_message"] = fine.get("dispute_message")
					updates["has_impound"] = 1 if fine.get("has_impound") else 0
					updates["has_declare"] = 1 if fine.get("has_declare") else 0
					updates["raw_data"] = json.dumps(fine, default=str)

				if updates:
					frappe.db.set_value("Traffic Fine", current.name, updates)

				# Save ticket photo if not yet saved
				if not current.ticket_photo and fine.get("ticket_photo") and fine.get("ticket_photo") != "null":
					_save_ticket_photo(current.name, fine_number, fine.get("ticket_photo"))

				continue

			# Resolve vehicle from plate info if not provided
			fine_vehicle = vehicle
			if not fine_vehicle:
				plate_no = fine.get("plate_number")
				if plate_no:
					fine_vehicle = frappe.db.get_value("Vehicle", {"plate_no": plate_no}, "name")
					if not fine_vehicle:
						fine_vehicle = frappe.db.get_value(
							"Vehicle",
							{"plate_no": ["like", f"%{plate_no}%"]},
							"name"
						)

			# Find agreement for this vehicle on the fine date
			fine_date_parsed = _parse_fine_date_to_date(fine.get("fine_date"))
			agreement_type, agreement_name, customer = _find_agreement_for_vehicle(fine_vehicle, fine_date_parsed)

			fine_doc = frappe.new_doc("Traffic Fine")
			fine_doc.vehicle = fine_vehicle
			fine_doc.fine_number = fine.get("fine_number")
			fine_doc.paid = is_paid_to_rta
			if is_paid_to_rta:
				fine_doc.charged_to_customer = 1
			fine_doc.fine_date = fine.get("fine_date")
			fine_doc.fine_time = fine.get("fine_time")
			fine_doc.plate_source = fine.get("plate_source")
			fine_doc.plate_category = fine.get("plate_category")
			fine_doc.plate_code = fine.get("plate_code")
			fine_doc.plate_number = fine.get("plate_number")
			fine_doc.vehicle_info = fine.get("vehicle_info")
			fine_doc.location = fine.get("location")
			fine_doc.source = fine.get("source")
			fine_doc.details = fine.get("details")
			fine_doc.amount = fine.get("amount", 0)
			fine_doc.black_points = fine.get("black_points")
			fine_doc.api_fine_id = str(fine.get("id"))
			fine_doc.scraped_at = fine.get("scraped_at")

			# New fields from updated API response
			fine_doc.ticket_id = fine.get("ticket_id")
			fine_doc.traffic_fine_id = fine.get("traffic_fine_id")
			fine_doc.ticket_type = fine.get("ticket_type")
			fine_doc.chassis_no = fine.get("chassis_no")
			fine_doc.vehicle_id = fine.get("vehicle_id")
			fine_doc.traffic_file_id = fine.get("traffic_file_id")
			fine_doc.dispute_url = fine.get("dispute_url")
			fine_doc.dispute_message = fine.get("dispute_message")
			fine_doc.has_impound = 1 if fine.get("has_impound") else 0
			fine_doc.has_declare = 1 if fine.get("has_declare") else 0

			fine_doc.raw_data = json.dumps(fine, default=str)

			# Link to agreement
			if agreement_type == "lease":
				fine_doc.lease_agreement = agreement_name
				fine_doc.linked_contract = agreement_name
			elif agreement_type == "rental":
				fine_doc.linked_agreement = agreement_name

			fine_doc.insert(ignore_permissions=True)
			new_count += 1

			# Save ticket_photo as file attachment if present
			ticket_photo_b64 = fine.get("ticket_photo")
			if ticket_photo_b64 and ticket_photo_b64 != "null":
				_save_ticket_photo(fine_doc.name, fine_doc.fine_number, ticket_photo_b64)

			frappe.logger().info(f"Saved fine: {fine_doc.name} - {fine_doc.fine_number} -> {agreement_type}: {agreement_name}")

		except Exception as e:
			frappe.log_error(title="RTA Fines Save", message=f"Error saving fine {fine.get('fine_number')}: {str(e)}")
			continue

	frappe.db.commit()
	return new_count


@frappe.whitelist()
def sync_all_vehicles_fines():
	"""Sync traffic fines from the RTA fines API.

	Fetches all fines from the central /fines endpoint and saves new ones.
	Also attempts per-vehicle scraping for vehicles with full plate info.
	"""
	try:
		# Get or create API Status record
		api_status_name = "RTA Traffic Fines"
		if not frappe.db.exists("API Status", api_status_name):
			api_status = frappe.new_doc("API Status")
			api_status.api_name = api_status_name
			api_status.api_type = "RTA Traffic Fines"
			api_status.enabled = 1
			api_status.insert(ignore_permissions=True)

		frappe.db.set_value("API Status", api_status_name, {
			"status": "Running",
			"last_sync_time": datetime.now(),
		})

		api = RTAFinesAPI()

		# Fetch all fines from central endpoint (including paid status)
		fines_data = api.get_fines(limit=1000, include_paid=True)

		total_new = 0
		if fines_data and fines_data.get("fines"):
			total_new = save_fines_to_doctype(fines_data["fines"])

		# Update status as success
		_update_rta_fines_status("Success", records_fetched=total_new)

		# Send notifications if new fines were found
		if total_new > 0:
			try:
				from right_hire.right_hire.notifications import check_and_send_notifications_after_sync
				check_and_send_notifications_after_sync()
			except Exception as e:
				frappe.log_error(title="RTA Notifications", message=f"Failed to send notifications: {str(e)}")

		return {
			"status": "success",
			"total_fines_from_api": fines_data.get("total", 0) if fines_data else 0,
			"new_fines": total_new,
		}

	except Exception as e:
		error_msg = f"RTA fines sync error: {str(e)[:200]}"
		frappe.log_error(error_msg, "RTA Fines Sync")
		_update_rta_fines_status("Failed", error_message=error_msg)
		return {"status": "error", "message": error_msg}


def _update_rta_fines_status(status, records_fetched=0, error_message=None):
	"""Update the RTA Traffic Fines API Status record."""
	try:
		if error_message and len(error_message) > 140:
			error_message = error_message[:140]
		if frappe.db.exists("API Status", "RTA Traffic Fines"):
			doc = frappe.get_doc("API Status", "RTA Traffic Fines")
			doc.update_status(status, records_fetched=records_fetched, error_message=error_message)
	except Exception:
		try:
			frappe.db.set_value("API Status", "RTA Traffic Fines", "status", status)
			frappe.db.commit()
		except Exception:
			pass


def sync_before_contract_closure(doc, method=None):
	"""
	Sync RTA fines before closing a contract
	Called from document event hook (before_submit)
	"""
	try:
		settings = frappe.get_single("RTA Settings")
		if not settings.enabled or not settings.sync_before_contract_closure:
			return

		# Get vehicle from contract
		vehicle = doc.vehicle if hasattr(doc, 'vehicle') else None
		if not vehicle:
			return

		# Sync for this vehicle only
		result = sync_vehicle_fines(vehicle=vehicle)

		if result.get("status") == "success" and result.get('new_fines', 0) > 0:
			frappe.msgprint(
				f"RTA Fines synced: {result.get('new_fines', 0)} new fines found",
				indicator="orange",
				alert=True
			)
		elif result.get("status") == "error":
			frappe.msgprint(
				f"RTA Fines sync warning: {result.get('message', 'Unknown error')}",
				indicator="orange",
				alert=True
			)

	except Exception as e:
		frappe.log_error(title="RTA Fines Integration", message=f"Sync before closure error: {str(e)}")


def _save_ticket_photo(fine_name, fine_number, base64_data):
	"""Save a base64-encoded ticket photo as a file attachment on the Traffic Fine."""
	import base64

	try:
		# Strip data URI prefix if present (e.g. "data:image/jpeg;base64,...")
		if "," in base64_data:
			base64_data = base64_data.split(",", 1)[1]

		file_content = base64.b64decode(base64_data)

		# Determine file extension from content
		ext = "jpg"
		if file_content[:4] == b'\x89PNG':
			ext = "png"

		filename = f"ticket_photo_{fine_number}.{ext}"

		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": filename,
			"attached_to_doctype": "Traffic Fine",
			"attached_to_name": fine_name,
			"attached_to_field": "ticket_photo",
			"content": file_content,
			"is_private": 1,
		})
		file_doc.save(ignore_permissions=True)

		# Update the ticket_photo field with the file URL
		frappe.db.set_value("Traffic Fine", fine_name, "ticket_photo", file_doc.file_url, update_modified=False)

	except Exception as e:
		frappe.log_error(title="RTA Ticket Photo", message=f"Error saving ticket photo for {fine_name}: {str(e)}")
