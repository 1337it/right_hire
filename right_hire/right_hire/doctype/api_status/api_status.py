# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta

class APIStatus(Document):
	def update_status(self, status, job_id=None, records_fetched=0, error_message=None):
		"""Update API status after a sync attempt"""
		self.status = status
		self.last_sync_time = datetime.now()

		if job_id:
			self.last_job_id = job_id

		if status == "Success":
			self.records_fetched = records_fetched
			self.total_records = (self.total_records or 0) + records_fetched
			self.last_success_time = datetime.now()
			self.error_count = 0
			self.last_error_message = None
		elif status == "Failed":
			self.error_count = (self.error_count or 0) + 1
			self.last_error_message = error_message

		# Calculate next sync time
		if self.auto_sync and self.sync_frequency_hours:
			self.next_sync_time = datetime.now() + timedelta(hours=self.sync_frequency_hours)

		self.save(ignore_permissions=True)

	def mark_running(self, job_id):
		"""Mark API as currently running"""
		self.status = "Running"
		self.last_job_id = job_id
		self.save(ignore_permissions=True)

	def mark_started(self, job_id):
		"""Mark API sync as started"""
		self.status = "Started"
		self.last_job_id = job_id
		self.last_sync_time = datetime.now()
		self.save(ignore_permissions=True)


@frappe.whitelist()
def get_api_status_summary():
	"""Get summary of all API statuses for dashboard widget"""
	statuses = frappe.get_all(
		"API Status",
		fields=["name", "api_name", "api_type", "status", "last_sync_time",
		        "last_error_message", "records_fetched", "error_count", "enabled"],
		filters={"enabled": 1}
	)

	return statuses


@frappe.whitelist()
def trigger_manual_sync(api_name):
	"""Manually trigger sync for a specific API"""
	api_status = frappe.get_doc("API Status", api_name)

	if not api_status.enabled:
		frappe.throw("API is disabled")

	if api_status.api_type == "RTA Traffic Fines":
		from right_hire.right_hire.rta_fines_integration import sync_all_vehicles_fines
		return sync_all_vehicles_fines()
	elif api_status.api_type == "Salik Trips":
		from right_hire.right_hire.salik_integration import sync_salik_data
		return sync_salik_data()
	elif api_status.api_type == "Darb Tolls":
		from right_hire.right_hire.darb_integration import sync_darb_data
		return sync_darb_data()
	else:
		frappe.throw("Unknown API type")
