# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, now_datetime, get_datetime


class NRMAgreement(Document):
	def validate(self):
		self.set_vehicle_details()
		self.set_assigned_person_details()
		self.calculate_totals()
		self.validate_dates()
		self.validate_vehicle_availability()

	def before_submit(self):
		self.update_vehicle_status("NRM")

	def on_cancel(self):
		self.update_vehicle_status("Available")

	def on_update_after_submit(self):
		if self.status == "Completed" and self.date_in:
			self.update_vehicle_status("Available")
			self.calculate_totals()

	def set_vehicle_details(self):
		"""Fetch and set vehicle details"""
		if self.vehicle:
			vehicle = frappe.get_doc("Vehicle", self.vehicle)

			# Set make and model
			make = vehicle.get("make") or ""
			model = vehicle.get("model") or ""
			self.make_and_model = f"{make} {model}".strip()

			# Set plate number - try different field names
			if not self.vehicle_plate:
				self.vehicle_plate = (
					vehicle.get("license_plate") or
					vehicle.get("plate_number") or
					vehicle.get("registration_number") or
					vehicle.name
				)

			# Set body type
			self.body_type = vehicle.get("body_type") or ""

	def set_assigned_person_details(self):
		"""Set assigned person name and details based on type"""
		self.assigned_person_name = ""
		self.staff_code = ""
		self.contact_number = ""

		if self.assigned_to_type == "Staff" and self.staff:
			emp = frappe.get_doc("Employee", self.staff)
			self.assigned_person_name = emp.employee_name
			self.staff_code = emp.name
			self.contact_number = emp.get("cell_number") or emp.get("personal_email") or ""

		elif self.assigned_to_type == "Driver" and self.driver:
			driver = frappe.get_doc("Driver", self.driver)
			self.assigned_person_name = driver.full_name or driver.name
			self.staff_code = driver.name
			self.contact_number = driver.get("cell_number") or ""

		elif self.assigned_to_type == "Customer" and self.customer:
			customer = frappe.get_doc("Customer", self.customer)
			self.assigned_person_name = customer.customer_name
			self.staff_code = customer.name
			# Try to get primary contact
			contact = frappe.db.get_value(
				"Dynamic Link",
				{"link_doctype": "Customer", "link_name": self.customer, "parenttype": "Contact"},
				"parent"
			)
			if contact:
				self.contact_number = frappe.db.get_value("Contact", contact, "mobile_no") or ""

		elif self.assigned_to_type == "Other" and self.other_name:
			self.assigned_person_name = self.other_name

	def calculate_totals(self):
		"""Calculate total days and km travelled"""
		# Calculate total days
		if self.date_out:
			end_date = self.date_in or now_datetime()
			self.total_days = max(1, date_diff(end_date, self.date_out) + 1)

		# Calculate km travelled
		if self.odometer_out and self.odometer_in:
			self.km_travelled = max(0, self.odometer_in - self.odometer_out)
		else:
			self.km_travelled = 0

	def validate_dates(self):
		"""Validate date_out and date_in"""
		if self.date_in and self.date_out:
			if get_datetime(self.date_in) < get_datetime(self.date_out):
				frappe.throw(_("Date In cannot be before Date Out"))

	def validate_vehicle_availability(self):
		"""Check if vehicle is available for NRM"""
		if not self.vehicle:
			return

		# Skip validation if this is an existing document being updated
		if not self.is_new():
			return

		# Check for active NRM agreements
		existing_nrm = frappe.db.exists(
			"NRM Agreement",
			{
				"vehicle": self.vehicle,
				"status": "Active",
				"docstatus": 1,
				"name": ["!=", self.name]
			}
		)
		if existing_nrm:
			frappe.throw(
				_("Vehicle {0} already has an active NRM Agreement: {1}").format(
					self.vehicle, existing_nrm
				)
			)

		# Check for active rental/lease agreements
		vehicle_doc = frappe.get_doc("Vehicle", self.vehicle)
		current_status = vehicle_doc.get("status") or vehicle_doc.get("vehicle_status")

		if current_status in ["On Rent", "On Lease", "Reserved"]:
			frappe.throw(
				_("Vehicle {0} is currently {1} and cannot be assigned to NRM").format(
					self.vehicle, current_status
				)
			)

	def update_vehicle_status(self, status):
		"""Update vehicle status"""
		if not self.vehicle:
			return

		try:
			vehicle = frappe.get_doc("Vehicle", self.vehicle)

			# Try different field names for status
			if hasattr(vehicle, "status"):
				vehicle.status = status
			elif hasattr(vehicle, "vehicle_status"):
				vehicle.vehicle_status = status

			vehicle.flags.ignore_validate_update_after_submit = True
			vehicle.save(ignore_permissions=True)

		except Exception as e:
			frappe.log_error(f"Failed to update vehicle status: {e}", "NRM Agreement")

	def complete_nrm(self, date_in=None, odometer_in=None, fuel_level_in=None):
		"""Mark NRM as completed"""
		if self.docstatus != 1:
			frappe.throw(_("Only submitted NRM Agreements can be completed"))

		self.status = "Completed"
		self.date_in = date_in or now_datetime()

		if odometer_in:
			self.odometer_in = odometer_in
		if fuel_level_in:
			self.fuel_level_in = fuel_level_in

		self.calculate_totals()
		self.flags.ignore_validate_update_after_submit = True
		self.save(ignore_permissions=True)

		# Update vehicle status
		self.update_vehicle_status("Available")

		return self.name


@frappe.whitelist()
def complete_nrm_agreement(nrm_name, date_in=None, odometer_in=None, fuel_level_in=None):
	"""API to complete an NRM Agreement"""
	doc = frappe.get_doc("NRM Agreement", nrm_name)
	return doc.complete_nrm(date_in, odometer_in, fuel_level_in)


@frappe.whitelist()
def get_vehicle_details(vehicle):
	"""Get vehicle details for NRM form"""
	if not vehicle:
		return {}

	vehicle_doc = frappe.get_doc("Vehicle", vehicle)

	make = vehicle_doc.get("make") or ""
	model = vehicle_doc.get("model") or ""

	return {
		"make_and_model": f"{make} {model}".strip(),
		"vehicle_type": vehicle_doc.get("vehicle_type") or "",
		"vehicle_plate": vehicle_doc.get("license_plate") or vehicle,
		"current_odometer": vehicle_doc.get("last_odometer") or vehicle_doc.get("odometer") or 0
	}
