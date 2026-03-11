"""
Salik Integration Module
Updated to use Salik Trips API instead of Selenium web scraping
Includes Toll Schedule detection (Peak/Low-Peak/Off-Peak) based on UAE government timing
"""

import frappe
import requests
import time
import json
from datetime import datetime, timedelta


# Time slots for normal timing (Mon-Sat and Sunday)
NORMAL_TIME_SLOTS = {
	"peak": [(6, 10), (16, 20)],       # 6-10 AM, 4-8 PM
	"low_peak": [(10, 16), (20, 25)],  # 10 AM-4 PM, 8 PM-1 AM (25 = 1 AM next day)
	"off_peak": [(1, 6)]                # 1-6 AM
}

# Time slots for Ramadan timing
RAMADAN_TIME_SLOTS = {
	"peak": [(9, 17)],                  # 9 AM - 5 PM
	"low_peak": [(7, 9), (17, 26)],     # 7-9 AM, 5 PM-2 AM (26 = 2 AM next day)
	"off_peak": [(2, 7)]                # 2-7 AM
}


def get_toll_schedule(transaction_date, transaction_time, is_ramadan=None):
	"""
	Determine the toll schedule (Peak/Low-Peak/Off-Peak) based on transaction time.

	Args:
		transaction_date: Date object or string (YYYY-MM-DD)
		transaction_time: Time string (HH:MM or HH:MM:SS)
		is_ramadan: Override for Ramadan timing (if None, reads from settings)

	Returns:
		str: "Peak", "Low-Peak", or "Off-Peak"
	"""
	# Parse time - handle various formats (string, time, timedelta)
	hour = 0
	if isinstance(transaction_time, str):
		try:
			if len(transaction_time) > 5:
				time_obj = datetime.strptime(transaction_time, '%H:%M:%S').time()
			else:
				time_obj = datetime.strptime(transaction_time, '%H:%M').time()
			hour = time_obj.hour
		except:
			hour = 0
	elif hasattr(transaction_time, 'hour'):
		# datetime.time object
		hour = transaction_time.hour
	elif hasattr(transaction_time, 'total_seconds'):
		# timedelta object (from database Time field)
		total_seconds = int(transaction_time.total_seconds())
		hour = (total_seconds // 3600) % 24
	else:
		hour = 0

	# Use 24+ for times after midnight that belong to previous day's schedule
	if hour < 6:  # Times between midnight and 6 AM
		hour += 24  # Treat as continuation of previous day's schedule

	# Check if Ramadan timing is active
	if is_ramadan is None:
		try:
			settings = frappe.get_single("Salik Settings")
			is_ramadan = settings.is_ramadan_timing
		except:
			is_ramadan = False

	# Select time slots based on Ramadan setting
	time_slots = RAMADAN_TIME_SLOTS if is_ramadan else NORMAL_TIME_SLOTS

	# Determine schedule based on time
	schedule = "off_peak"  # Default
	for slot_name, slots in time_slots.items():
		for start, end in slots:
			if start <= hour < end:
				schedule = slot_name
				break

	# Convert schedule name to display format
	schedule_display = {
		"peak": "Peak",
		"low_peak": "Low-Peak",
		"off_peak": "Off-Peak"
	}

	return schedule_display.get(schedule, "Off-Peak")


@frappe.whitelist()
def backfill_toll_schedules():
	"""
	Backfill toll_schedule for existing Salik Transactions that don't have it set.
	Can be called from console or as a one-time patch.
	"""
	transactions = frappe.get_all(
		"Salik Transaction",
		filters=[["toll_schedule", "in", ["", None]]],
		fields=["name", "transaction_date", "transaction_time"]
	)

	updated = 0
	for trans in transactions:
		if trans.transaction_time:
			schedule = get_toll_schedule(trans.transaction_date, trans.transaction_time)
			frappe.db.set_value("Salik Transaction", trans.name, "toll_schedule", schedule, update_modified=False)
			updated += 1

	frappe.db.commit()
	frappe.msgprint(f"Updated {updated} transactions with toll schedule")
	return {"updated": updated, "total": len(transactions)}


class SalikAPI:
	"""Salik Trips API client"""

	def __init__(self):
		self.settings = frappe.get_single("Salik Settings")
		if not self.settings.enabled:
			frappe.throw("Salik Integration is disabled")

		self.base_url = self.settings.api_base_url or "http://139.185.53.79:8000/api"
		self.api_key = self.settings.get_password("api_key")

		if not self.api_key:
			frappe.throw("API Key not configured in Salik Settings")

		self.headers = {
			"X-API-Key": self.api_key,
			"Content-Type": "application/json"
		}

	def trigger_scraping(self, filter_days=7, account_id=None):
		"""Trigger Salik trips scraping"""
		url = f"{self.base_url}/scrape/salik"

		payload = {
			"filter_days": filter_days
		}

		if account_id:
			payload["account_id"] = account_id

		frappe.logger().info(f"Triggering Salik trips scraping for last {filter_days} days")

		try:
			response = requests.post(url, json=payload, headers=self.headers, timeout=30)
			response.raise_for_status()
			result = response.json()

			frappe.logger().info(f"Scraping job started: {result.get('job_id')}")
			return result
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="Salik API", message=f"Failed to trigger scraping: {str(e)}")
			return None

	def check_job_status(self, job_id):
		"""Check the status of a scraping job"""
		url = f"{self.base_url}/status/{job_id}"

		try:
			response = requests.get(url, headers=self.headers, timeout=30)
			response.raise_for_status()
			return response.json()
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="Salik API", message=f"Failed to check job status: {str(e)}")
			return None

	def get_trips(self, start_date=None, end_date=None, vehicle=None, limit=100, offset=0):
		"""Retrieve trips from the API"""
		url = f"{self.base_url}/trips"

		params = {"limit": limit, "offset": offset}

		if start_date:
			params["start_date"] = start_date.strftime("%Y-%m-%d") if isinstance(start_date, datetime) else start_date
		if end_date:
			params["end_date"] = end_date.strftime("%Y-%m-%d") if isinstance(end_date, datetime) else end_date
		if vehicle:
			params["vehicle"] = vehicle

		try:
			response = requests.get(url, params=params, headers=self.headers, timeout=30)
			response.raise_for_status()
			return response.json()
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="Salik API", message=f"Failed to retrieve trips: {str(e)}")
			return None

	def get_trip_by_id(self, trip_id):
		"""Get a specific trip by its API ID"""
		url = f"{self.base_url}/trips/{trip_id}"

		try:
			response = requests.get(url, headers=self.headers, timeout=30)
			response.raise_for_status()
			return response.json()
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="Salik API", message=f"Failed to retrieve trip {trip_id}: {str(e)}")
			return None

	def get_vehicles(self):
		"""Retrieve vehicles from the API"""
		url = f"{self.base_url}/vehicles"

		try:
			response = requests.get(url, headers=self.headers, timeout=60)
			response.raise_for_status()
			return response.json()
		except requests.exceptions.RequestException as e:
			frappe.log_error(title="Salik API", message=f"Failed to retrieve vehicles: {str(e)}")
			return None


def sync_salik_vehicles(api):
	"""Sync vehicles from Salik API to the system"""
	import base64

	vehicles_data = api.get_vehicles()

	if not vehicles_data or not vehicles_data.get("vehicles"):
		frappe.logger().info("No vehicles found in Salik API")
		return {"synced": 0, "new": 0}

	synced_count = 0
	new_count = 0

	for veh in vehicles_data.get("vehicles", []):
		try:
			plate_number = veh.get("plate_number", "").strip()
			plate_type = veh.get("plate_type", "").strip()
			plate_category = veh.get("plate_category", "").strip()
			salik_vehicle_id = veh.get("id", "")

			if not plate_number:
				continue

			# Parse raw_data for images
			raw_data = {}
			if veh.get("raw_data"):
				try:
					raw_data = json.loads(veh.get("raw_data"))
				except:
					pass

			# Try to find existing vehicle by plate number
			existing_vehicle = None
			vehicles = frappe.get_all(
				"Vehicle",
				filters=[["plate_no", "like", f"%{plate_number}%"]],
				fields=["name", "plate_no", "salik_account_linked", "salik_vehicle_id", "rta_registration_front", "rta_registration_back"]
			)

			if vehicles:
				existing_vehicle = vehicles[0]

			vehicle_name = None

			if existing_vehicle:
				vehicle_name = existing_vehicle.name
				# Update existing vehicle with Salik info
				frappe.db.set_value("Vehicle", existing_vehicle.name, {
					"salik_account_linked": 1,
					"salik_vehicle_id": salik_vehicle_id
				}, update_modified=False)
				synced_count += 1
				frappe.logger().info(f"Updated vehicle {existing_vehicle.name} with Salik ID {salik_vehicle_id}")
			else:
				# Create new vehicle as draft
				new_vehicle = frappe.new_doc("Vehicle")
				new_vehicle.plate_no = f"{plate_type} {plate_number}"
				new_vehicle.salik_account_linked = 1
				new_vehicle.salik_vehicle_id = salik_vehicle_id
				new_vehicle.status = "Available"
				new_vehicle.ownership_type = "Company Owned"

				new_vehicle.flags.ignore_mandatory = True
				new_vehicle.insert(ignore_permissions=True)
				vehicle_name = new_vehicle.name
				new_count += 1
				frappe.logger().info(f"Created new vehicle {new_vehicle.name} from Salik: {plate_type} {plate_number}")

			# Save registration card images if available
			if vehicle_name and raw_data.get("images"):
				images = raw_data.get("images", [])

				# Check if images already exist for this vehicle
				current_front = frappe.db.get_value("Vehicle", vehicle_name, "rta_registration_front")
				current_back = frappe.db.get_value("Vehicle", vehicle_name, "rta_registration_back")

				# Only save if images don't exist yet
				if not current_front and len(images) > 0:
					front_url = save_registration_image(vehicle_name, images[0].get("image"), "front", plate_number)
					if front_url:
						frappe.db.set_value("Vehicle", vehicle_name, "rta_registration_front", front_url, update_modified=False)
						frappe.logger().info(f"Saved front registration image for {vehicle_name}")

				if not current_back and len(images) > 1:
					back_url = save_registration_image(vehicle_name, images[1].get("image"), "back", plate_number)
					if back_url:
						frappe.db.set_value("Vehicle", vehicle_name, "rta_registration_back", back_url, update_modified=False)
						frappe.logger().info(f"Saved back registration image for {vehicle_name}")

		except Exception as e:
			frappe.log_error(title="Salik Vehicle Sync", message=f"Error syncing vehicle: {str(e)}")
			continue

	frappe.db.commit()
	return {"synced": synced_count, "new": new_count}


def save_registration_image(vehicle_name, base64_data, side, plate_number):
	"""Save base64 image as File attachment and return the file URL"""
	import base64

	if not base64_data:
		return None

	try:
		# Decode base64 image
		image_data = base64.b64decode(base64_data)

		# Create filename
		filename = f"registration_{plate_number}_{side}.jpg"

		# Save as File
		file_doc = frappe.new_doc("File")
		file_doc.file_name = filename
		file_doc.attached_to_doctype = "Vehicle"
		file_doc.attached_to_name = vehicle_name
		file_doc.content = image_data
		file_doc.is_private = 0
		file_doc.save(ignore_permissions=True)

		return file_doc.file_url

	except Exception as e:
		frappe.log_error(title="Salik Image Save", message=f"Error saving image for {vehicle_name}: {str(e)}")
		return None


@frappe.whitelist()
def sync_salik_data(vehicle=None, skip_scrape=False):
	"""
	Main function to sync Salik data
	Can be called manually or via scheduled job

	Args:
		vehicle: Optional vehicle filter
		skip_scrape: If True, only fetch existing trips without triggering new scrape
	"""
	try:
		settings = frappe.get_single("Salik Settings")
		if not settings.enabled:
			return {"status": "disabled", "message": "Salik integration is disabled"}

		api = SalikAPI()

		# First sync vehicles from Salik API
		vehicle_result = sync_salik_vehicles(api)
		frappe.logger().info(f"Vehicle sync: {vehicle_result.get('synced', 0)} updated, {vehicle_result.get('new', 0)} new")

		# Get or create API Status record
		api_status_name = "Salik Trips"
		if not frappe.db.exists("API Status", api_status_name):
			api_status = frappe.new_doc("API Status")
			api_status.api_name = api_status_name
			api_status.api_type = "Salik Trips"
			api_status.filter_days = int(settings.salik_filter_days or 7)
			api_status.insert(ignore_permissions=True)
		else:
			api_status = frappe.get_doc("API Status", api_status_name)

		# Get filter days from settings
		filter_days = int(settings.salik_filter_days or 7)

		# If skip_scrape is True, just fetch existing trips
		if skip_scrape:
			return _fetch_and_save_trips(api, api_status, settings, filter_days, vehicle, vehicle_result=vehicle_result)

		# Trigger scraping
		result = api.trigger_scraping(filter_days=filter_days)

		if not result or not result.get("job_id"):
			# Scrape trigger failed - try to fetch existing trips anyway
			frappe.logger().warning("Failed to trigger scraping, fetching existing trips")
			return _fetch_and_save_trips(api, api_status, settings, filter_days, vehicle, vehicle_result=vehicle_result)

		job_id = result["job_id"]
		api_status.mark_started(job_id)

		# Wait for job to complete (with timeout)
		max_wait_time = 120  # 2 minutes
		wait_interval = 10  # 10 seconds
		elapsed_time = 0

		while elapsed_time < max_wait_time:
			status_result = api.check_job_status(job_id)

			if not status_result:
				break

			status = status_result.get("status")
			frappe.logger().info(f"Job {job_id} status: {status}")

			if status == "completed":
				# Job completed, fetch the trips
				return _fetch_and_save_trips(api, api_status, settings, filter_days, vehicle, job_id, vehicle_result=vehicle_result)

			elif status == "failed":
				error_msg = status_result.get("error_message", "Unknown error")
				api_status.update_status("Failed", job_id=job_id, error_message=error_msg)
				settings.last_error_message = error_msg
				settings.save(ignore_permissions=True)
				return {"status": "error", "message": error_msg, "vehicles_synced": vehicle_result.get("synced", 0) if vehicle_result else 0, "new_vehicles": vehicle_result.get("new", 0) if vehicle_result else 0}

			# Wait before checking again
			time.sleep(wait_interval)
			elapsed_time += wait_interval

		# Timeout - but still try to fetch existing trips
		frappe.logger().warning("Scraping timeout, fetching existing trips")
		return _fetch_and_save_trips(api, api_status, settings, filter_days, vehicle, job_id, vehicle_result=vehicle_result)

	except Exception as e:
		error_msg = str(e)
		frappe.log_error(title="Salik Sync Failed", message=error_msg)

		# Update error in settings
		settings = frappe.get_single("Salik Settings")
		settings.last_error_message = error_msg
		settings.save(ignore_permissions=True)
		frappe.db.commit()

		return {"status": "error", "message": error_msg}


def _fetch_and_save_trips(api, api_status, settings, filter_days, vehicle_filter=None, job_id=None, vehicle_result=None):
	"""Fetch trips from API and save to DocType"""
	start_date = datetime.now() - timedelta(days=filter_days)
	end_date = datetime.now()

	trips_data = api.get_trips(start_date=start_date, end_date=end_date)

	if trips_data and trips_data.get("trips"):
		new_count = save_trips_to_doctype(trips_data["trips"], vehicle_filter=vehicle_filter)

		api_status.update_status(
			"Success",
			job_id=job_id,
			records_fetched=new_count
		)

		# Update settings
		settings.last_successful_sync = datetime.now()
		settings.total_transactions_fetched = (settings.total_transactions_fetched or 0) + new_count
		settings.total_vehicles_synced = (settings.total_vehicles_synced or 0) + (vehicle_result.get("new", 0) if vehicle_result else 0)
		settings.save(ignore_permissions=True)

		return {
			"status": "success",
			"job_id": job_id,
			"total_trips": trips_data.get("total", 0),
			"new_transactions": new_count,
			"vehicles_synced": vehicle_result.get("synced", 0) if vehicle_result else 0,
			"new_vehicles": vehicle_result.get("new", 0) if vehicle_result else 0
		}
	else:
		api_status.update_status("Success", job_id=job_id, records_fetched=0)
		return {
			"status": "success",
			"job_id": job_id,
			"message": "No trips found",
			"vehicles_synced": vehicle_result.get("synced", 0) if vehicle_result else 0,
			"new_vehicles": vehicle_result.get("new", 0) if vehicle_result else 0
		}


def save_trips_to_doctype(trips, vehicle_filter=None):
	"""Save Salik trips to Salik Transaction DocType"""
	new_count = 0
	frappe.logger().info(f"Processing {len(trips)} trips")

	for trip in trips:
		try:
			# Parse vehicle plate - API returns "vehicle_id" field
			vehicle_plate = trip.get("vehicle_id", trip.get("vehicle", "")).strip()
			frappe.logger().info(f"Processing trip for vehicle: {vehicle_plate}")

			# Find matching vehicle
			vehicle_doc = None
			if vehicle_filter:
				vehicle_doc = frappe.get_doc("Vehicle", vehicle_filter)
			else:
				# Try to find vehicle by plate number or tag
				vehicles = frappe.get_all(
					"Vehicle",
					filters={"salik_account_linked": 1},
					fields=["name", "plate_no", "salik_tag_number"]
				)

				for v in vehicles:
					if v.plate_no and v.plate_no in vehicle_plate:
						vehicle_doc = frappe.get_doc("Vehicle", v.name)
						break
					if v.salik_tag_number and v.salik_tag_number == trip.get("tag_number"):
						vehicle_doc = frappe.get_doc("Vehicle", v.name)
						break

			if not vehicle_doc:
				frappe.logger().info(f"Vehicle not found for plate: {vehicle_plate}")
				continue

			# Parse trip date
			trip_date = datetime.strptime(trip.get("trip_date"), '%Y-%m-%d').date()

			# Create unique transaction ID using API id or composite key
			transaction_id = str(trip.get("id", f"{vehicle_plate}_{trip.get('trip_date')}_{trip.get('trip_time')}"))

			# Check if transaction already exists
			existing = frappe.db.exists("Salik Transaction", {"salik_transaction_id": transaction_id})

			if not existing:
				salik_trans = frappe.new_doc("Salik Transaction")
				salik_trans.vehicle = vehicle_doc.name
				salik_trans.salik_tag_number = vehicle_doc.salik_tag_number or trip.get("tag_number")
				salik_trans.plate_number = vehicle_doc.plate_no
				salik_trans.transaction_date = trip_date
				salik_trans.transaction_time = trip.get("trip_time", "00:00")
				salik_trans.gate_location = trip.get("gate") or trip.get("toll_gate")  # API uses "gate"
				salik_trans.direction = trip.get("direction")

				# Use toll amount from API - this is the source of truth
				salik_trans.toll_amount = float(trip.get("cost", 0))

				# Determine toll schedule from cost: 6 = Peak, 4 = Low-Peak, 0 = Off-Peak
				if salik_trans.toll_amount >= 6:
					salik_trans.toll_schedule = "Peak"
				elif salik_trans.toll_amount >= 4:
					salik_trans.toll_schedule = "Low-Peak"
				else:
					salik_trans.toll_schedule = "Off-Peak"

				salik_trans.status = "Unpaid"  # Default status
				salik_trans.sync_date = datetime.now()
				salik_trans.salik_transaction_id = transaction_id
				salik_trans.raw_data = json.dumps(trip)

				salik_trans.insert(ignore_permissions=True)
				new_count += 1

				frappe.logger().info(f"Saved transaction: {salik_trans.name} - {salik_trans.gate_location} ({salik_trans.toll_schedule}) - AED {salik_trans.toll_amount}")

			# Update vehicle sync status
			vehicle_doc.last_salik_sync = datetime.now()
			vehicle_doc.total_salik_charges = frappe.db.get_value(
				"Salik Transaction",
				{"vehicle": vehicle_doc.name, "paid": 0},
				"sum(toll_amount)"
			) or 0
			vehicle_doc.save(ignore_permissions=True)

		except Exception as e:
			frappe.log_error(title="Salik Sync", message=f"Error saving transaction: {str(e)}")
			continue

	frappe.db.commit()
	return new_count


def sync_before_contract_closure(doc, method=None):
	"""
	Sync Salik data before closing a contract
	Called from document event hook (before_submit)
	"""
	try:
		settings = frappe.get_single("Salik Settings")
		if not settings.enabled or not settings.sync_before_contract_closure:
			return

		# Get vehicle from contract
		vehicle = doc.vehicle if hasattr(doc, 'vehicle') else None
		if not vehicle:
			return

		# Sync for this vehicle only
		result = sync_salik_data(vehicle=vehicle)

		if result.get("status") == "success" and result.get('new_transactions', 0) > 0:
			frappe.msgprint(
				f"Salik data synced: {result.get('new_transactions', 0)} new transactions found",
				indicator="green",
				alert=True
			)
		elif result.get("status") == "error":
			frappe.msgprint(
				f"Salik sync warning: {result.get('message', 'Unknown error')}",
				indicator="orange",
				alert=True
			)

	except Exception as e:
		frappe.log_error(title="Salik Integration", message=f"Sync before closure error: {str(e)}")
