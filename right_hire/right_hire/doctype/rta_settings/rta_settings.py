# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document
from datetime import datetime

class RTASettings(Document):
	def validate(self):
		"""Validate API credentials if enabled"""
		if self.enabled and self.api_key and self.api_base_url:
			# Don't test on every save, only when explicitly requested
			pass

	def update_sync_status(self, success=True, vehicles_synced=0, fines_fetched=0, error_message=None):
		"""Update sync status after a sync operation"""
		if success:
			self.last_successful_sync = datetime.now()
			self.total_vehicles_synced = (self.total_vehicles_synced or 0) + vehicles_synced
			self.total_fines_fetched = (self.total_fines_fetched or 0) + fines_fetched
			self.last_error_message = None
		else:
			self.last_error_message = error_message

		self.save(ignore_permissions=True)
		frappe.db.commit()


@frappe.whitelist()
def test_api_connection():
	"""Test RTA API connection"""
	try:
		settings = frappe.get_single("RTA Settings")

		if not settings.api_base_url or not settings.api_key:
			return {
				"status": "error",
				"message": "API Base URL and API Key are required"
			}

		# Test connection by trying to get status of a dummy job
		# Or we could try to get fines with limit=0
		url = f"{settings.api_base_url}/fines"
		headers = {
			"X-API-Key": settings.get_password("api_key")
		}

		response = requests.get(url, headers=headers, params={"limit": 1}, timeout=10)

		if response.status_code == 200:
			settings.connection_status = f"✅ Connected successfully at {frappe.utils.now_datetime()}"
			settings.save(ignore_permissions=True)

			return {
				"status": "success",
				"message": "API connection successful",
				"response": response.json()
			}
		elif response.status_code == 401:
			settings.connection_status = f"❌ Authentication failed - Invalid API Key"
			settings.save(ignore_permissions=True)

			return {
				"status": "error",
				"message": "Authentication failed - Invalid API Key"
			}
		else:
			settings.connection_status = f"❌ Connection failed - HTTP {response.status_code}"
			settings.save(ignore_permissions=True)

			return {
				"status": "error",
				"message": f"Connection failed with status {response.status_code}"
			}

	except requests.exceptions.Timeout:
		settings = frappe.get_single("RTA Settings")
		settings.connection_status = f"❌ Connection timeout"
		settings.save(ignore_permissions=True)

		return {
			"status": "error",
			"message": "Connection timeout"
		}
	except requests.exceptions.ConnectionError:
		settings = frappe.get_single("RTA Settings")
		settings.connection_status = f"❌ Cannot reach API server"
		settings.save(ignore_permissions=True)

		return {
			"status": "error",
			"message": "Cannot reach API server"
		}
	except Exception as e:
		frappe.log_error(f"RTA API connection test failed: {str(e)}", "RTA Settings")
		settings = frappe.get_single("RTA Settings")
		settings.connection_status = f"❌ Error: {str(e)}"
		settings.save(ignore_permissions=True)

		return {
			"status": "error",
			"message": str(e)
		}


@frappe.whitelist()
def sync_now():
	"""Manually trigger RTA fines sync"""
	from right_hire.right_hire.rta_fines_integration import sync_all_vehicles_fines

	return sync_all_vehicles_fines()
