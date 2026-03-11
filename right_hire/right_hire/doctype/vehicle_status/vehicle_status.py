# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class VehicleStatus(Document):
	def validate(self):
		self.validate_transitions()

	def validate_transitions(self):
		"""Ensure no self-transitions"""
		for transition in self.allowed_transitions:
			if transition.target_status == self.status_name:
				frappe.throw(_("A status cannot transition to itself"))

	@staticmethod
	def get_allowed_next_statuses(current_status):
		"""Get list of statuses that current_status can transition to"""
		status_doc = frappe.get_doc("Vehicle Status", current_status)
		return [t.target_status for t in status_doc.allowed_transitions]

	@staticmethod
	def can_transition(from_status, to_status, user=None):
		"""Check if transition from from_status to to_status is allowed"""
		if not user:
			user = frappe.session.user

		try:
			status_doc = frappe.get_doc("Vehicle Status", from_status)
		except frappe.DoesNotExistError:
			return False, _("Status '{0}' not found").format(from_status)

		# Check if terminal status
		if status_doc.is_terminal:
			return False, _("Cannot transition from terminal status '{0}'").format(from_status)

		# Find the transition
		transition = None
		for t in status_doc.allowed_transitions:
			if t.target_status == to_status:
				transition = t
				break

		if not transition:
			return False, _("Transition from '{0}' to '{1}' is not allowed").format(from_status, to_status)

		# Check role permissions
		if transition.allowed_roles:
			allowed_roles = [r.strip() for r in transition.allowed_roles.split(",")]
			user_roles = frappe.get_roles(user)
			if not any(role in user_roles for role in allowed_roles):
				return False, _("You don't have permission to make this transition")

		return True, None


@frappe.whitelist()
def validate_status_change(vehicle, from_status, to_status):
	"""API to validate if a status change is allowed"""
	can_change, error = VehicleStatus.can_transition(from_status, to_status)

	# Check if reason is required
	requires_reason = False
	try:
		status_doc = frappe.get_doc("Vehicle Status", from_status)
		for t in status_doc.allowed_transitions:
			if t.target_status == to_status:
				requires_reason = t.requires_reason
				break
	except:
		pass

	return {
		"allowed": can_change,
		"error": error,
		"requires_reason": requires_reason
	}


def get_movement_type_for_transition(from_status, to_status):
	"""Map status transitions to movement types"""
	# Define movement type mappings
	movement_map = {
		# Going OUT movements
		("Available", "Out for Delivery"): ("Delivery", "out"),
		("Available", "Rented Out"): ("NRM - Customer Movement", "out"),
		("Available", "Leased"): ("NRM - Customer Movement", "out"),
		("Reserved", "Out for Delivery"): ("Delivery", "out"),
		("Reserved", "Rented Out"): ("NRM - Customer Movement", "out"),
		("Out for Delivery", "Rented Out"): ("NRM - Customer Movement", "out"),
		("Out for Delivery", "Leased"): ("NRM - Customer Movement", "out"),
		("Leased", "Out for Delivery"): ("Delivery", "out"),
		("Rented Out", "Out for Delivery"): ("Delivery", "out"),

		# Workshop/Maintenance movements
		("Available", "At Garage"): ("Workshop", "out"),
		("Available", "Under Maintenance"): ("Workshop", "out"),
		("At Garage", "Under Maintenance"): ("Workshop", "out"),

		# Custody movements
		("Rented Out", "Custody"): ("Custody", "out"),
		("Leased", "Custody"): ("Custody", "out"),
		("Due for Return", "Custody"): ("Custody", "out"),

		# Accident movements
		("Rented Out", "Accident/Repair"): ("Workshop", "out"),
		("Leased", "Accident/Repair"): ("Workshop", "out"),

		# Coming IN movements (returning to available)
		("Due for Return", "Available"): ("NRM - Customer Movement", "in"),
		("Due for Return", "At Garage"): ("NRM - Customer Movement", "in"),
		("Rented Out", "Due for Return"): None,  # No movement, just status change
		("Leased", "Due for Return"): None,  # No movement, just status change
		("At Garage", "Available"): ("Workshop", "in"),
		("Under Maintenance", "Available"): ("Workshop", "in"),
		("Under Maintenance", "At Garage"): ("Workshop", "in"),
		("Custody", "Available"): ("Custody", "in"),
		("Custody", "At Garage"): ("Custody", "in"),
		("Accident/Repair", "Available"): ("Workshop", "in"),
		("Accident/Repair", "Under Maintenance"): ("Workshop", "in"),

		# Recovery
		("Reserved", "Available"): ("Recovery", "in"),
		("Out for Delivery", "Available"): ("Recovery", "in"),
	}

	return movement_map.get((from_status, to_status))


@frappe.whitelist()
def change_vehicle_status(vehicle, to_status, movement_data=None):
	"""Change vehicle status with validation, logging, and movement creation"""
	import json

	vehicle_doc = frappe.get_doc("Vehicle", vehicle)
	from_status = vehicle_doc.status

	# Parse movement data
	data = {}
	if movement_data:
		try:
			data = json.loads(movement_data) if isinstance(movement_data, str) else movement_data
		except:
			data = {}

	reason = data.get('reason')

	# Validate transition
	can_change, error = VehicleStatus.can_transition(from_status, to_status)
	if not can_change:
		frappe.throw(error)

	# Check if reason is required
	try:
		status_doc = frappe.get_doc("Vehicle Status", from_status)
		for t in status_doc.allowed_transitions:
			if t.target_status == to_status and t.requires_reason and not reason:
				frappe.throw(_("Reason is required for this status change"))
				break
	except frappe.DoesNotExistError:
		pass

	# Create Movement record if applicable
	movement_info = get_movement_type_for_transition(from_status, to_status)
	movement_name = None

	if movement_info:
		movement_type_default, direction = movement_info
		# Use movement_type from data if provided, otherwise use default
		movement_type = data.get('movement_type', movement_type_default)

		movement_name = create_movement_for_status_change(
			vehicle=vehicle,
			vehicle_doc=vehicle_doc,
			movement_type=movement_type,
			direction=direction,
			movement_data=data,
			from_status=from_status,
			to_status=to_status
		)

	# Update vehicle status
	vehicle_doc.status = to_status

	# Update vehicle odometer based on direction
	direction = data.get('direction', 'out')
	mileage = data.get('out_mileage') if direction == 'out' else data.get('in_mileage')
	fuel = data.get('out_fuel_percentage') if direction == 'out' else data.get('in_fuel_percentage')

	if mileage:
		vehicle_doc.odometer = mileage

	if fuel is not None:
		vehicle_doc.fuel_level = fuel

	vehicle_doc.save()

	# Create status log
	frappe.get_doc({
		"doctype": "Vehicle Status Log",
		"vehicle": vehicle,
		"from_status": from_status,
		"to_status": to_status,
		"changed_at": frappe.utils.now(),
		"changed_by": frappe.session.user,
		"reason": reason,
		"reference_doctype": "Movements" if movement_name else None,
		"reference_name": movement_name
	}).insert(ignore_permissions=True)

	frappe.db.commit()

	return {
		"success": True,
		"message": _("Vehicle status changed from '{0}' to '{1}'").format(from_status, to_status),
		"movement": movement_name
	}


def create_movement_for_status_change(vehicle, vehicle_doc, movement_type, direction,
									   movement_data=None, from_status=None, to_status=None):
	"""Create a Movement record for the status change with all fields from dialog"""

	data = movement_data or {}

	movement = frappe.new_doc("Movements")
	movement.vehicle = vehicle
	movement.movement_type = movement_type
	movement.date = frappe.utils.today()
	movement.movement_subtype = f"Kanban: {from_status} → {to_status}"

	# Set agreement info if provided
	if data.get('agreement_type'):
		movement.agreement_type = data.get('agreement_type')
	if data.get('agreement_no'):
		movement.agreement_no = data.get('agreement_no')
	if data.get('workshop'):
		movement.workshop = data.get('workshop')

	# Helper function to add condition checklist items
	def add_condition_items(checklist_field, prefix):
		"""Add condition items to the specified checklist"""
		condition_map = {
			'body_condition': 'Body',
			'interior_condition': 'Interior - Seats',
			'tires_condition': 'Tires - Front Left',  # Representative tire
			'cleanliness': 'Cleanliness'
		}
		for field_suffix, item_name in condition_map.items():
			field_name = prefix + field_suffix
			condition_value = data.get(field_name)
			if condition_value:
				movement.append(checklist_field, {
					'item': item_name,
					'condition': condition_value,
					'remarks': ''
				})

		# Add damage notes as remarks on "Other" item if present
		damage_notes = data.get(prefix + 'damage_notes')
		if damage_notes:
			movement.append(checklist_field, {
				'item': 'Other',
				'condition': 'Damaged' if data.get('has_new_damage') else 'Fair',
				'remarks': damage_notes
			})

	# Set status based on direction
	if direction == "out":
		movement.status = "Out Only"

		# OUT fields from dialog
		movement.out_date_time = data.get('out_date_time') or frappe.utils.now()
		movement.out_mileage = data.get('out_mileage') or vehicle_doc.odometer
		movement.out_fuel_level = data.get('out_fuel_level')
		movement.out_fuel_percentage = data.get('out_fuel_percentage') or vehicle_doc.fuel_level
		movement.out_staff = data.get('out_staff')
		movement.out_customer = data.get('out_customer')
		movement.out_driver = data.get('out_driver')
		movement.out_notes = data.get('out_notes') or data.get('reason')
		movement.out_branch = vehicle_doc.branch

		# Add OUT condition checklist
		add_condition_items('out_vehicle_condition_checklist', 'out_')

	elif direction == "in":
		movement.status = "Returned"

		# IN fields from dialog
		in_date_time = data.get('in_date_time') or frappe.utils.now()
		in_mileage = data.get('in_mileage') or vehicle_doc.odometer
		in_fuel_level = data.get('in_fuel_level')
		in_fuel_percentage = data.get('in_fuel_percentage') or vehicle_doc.fuel_level
		in_staff = data.get('in_staff')
		in_customer = data.get('in_customer')
		in_driver = data.get('in_driver')
		in_notes = data.get('in_notes') or data.get('reason')
		in_branch = vehicle_doc.branch

		# Try to find and link to the last OUT movement for this vehicle
		last_out_movement = frappe.db.get_value(
			"Movements",
			filters={
				"vehicle": vehicle,
				"status": "Out Only"
			},
			fieldname="name",
			order_by="creation desc"
		)

		if last_out_movement:
			# Update the previous movement to Returned and add IN details
			prev_movement = frappe.get_doc("Movements", last_out_movement)
			prev_movement.status = "Returned"
			prev_movement.in_date_time = in_date_time
			prev_movement.in_mileage = in_mileage
			prev_movement.in_fuel_level = in_fuel_level
			prev_movement.in_fuel_percentage = in_fuel_percentage
			prev_movement.in_staff = in_staff
			prev_movement.in_customer = in_customer
			prev_movement.in_driver = in_driver
			prev_movement.in_notes = in_notes
			prev_movement.in_branch = in_branch

			# Calculate distance traveled
			if prev_movement.out_mileage and in_mileage:
				prev_movement.distance_traveled = (in_mileage or 0) - (prev_movement.out_mileage or 0)

			# Add IN condition checklist to existing movement
			condition_map = {
				'in_body_condition': 'Body',
				'in_interior_condition': 'Interior - Seats',
				'in_tires_condition': 'Tires - Front Left',
				'in_cleanliness': 'Cleanliness'
			}
			for field_name, item_name in condition_map.items():
				condition_value = data.get(field_name)
				if condition_value:
					prev_movement.append('in_vehicle_condition_checklist', {
						'item': item_name,
						'condition': condition_value,
						'remarks': ''
					})

			# Add damage notes as remarks on "Other" item if present
			in_damage_notes = data.get('in_damage_notes')
			if in_damage_notes:
				prev_movement.append('in_vehicle_condition_checklist', {
					'item': 'Other',
					'condition': 'Damaged' if data.get('has_new_damage') else 'Fair',
					'remarks': in_damage_notes
				})

			prev_movement.save(ignore_permissions=True)
			return prev_movement.name

		# If no previous OUT movement, create new IN movement
		movement.in_date_time = in_date_time
		movement.in_mileage = in_mileage
		movement.in_fuel_level = in_fuel_level
		movement.in_fuel_percentage = in_fuel_percentage
		movement.in_staff = in_staff
		movement.in_customer = in_customer
		movement.in_driver = in_driver
		movement.in_notes = in_notes
		movement.in_branch = in_branch

		# Add IN condition checklist for new movement
		add_condition_items('in_vehicle_condition_checklist', 'in_')

	movement.insert(ignore_permissions=True)
	return movement.name


@frappe.whitelist()
def get_movement_details_required(from_status, to_status):
	"""Check if movement details are required for this transition"""
	movement_info = get_movement_type_for_transition(from_status, to_status)

	if not movement_info:
		return {
			"requires_movement": False,
			"movement_type": None,
			"direction": None
		}

	movement_type, direction = movement_info
	return {
		"requires_movement": True,
		"movement_type": movement_type,
		"direction": direction
	}


@frappe.whitelist()
def get_vehicle_active_agreement(vehicle):
	"""Get the active agreement (Lease or Rental) for a vehicle"""
	# Check for active Lease Agreement
	lease = frappe.db.get_value(
		"Lease Agreement",
		filters={
			"vehicle": vehicle,
			"docstatus": 1,
			"lease_status": ["in", ["Active", "Due for Return"]]
		},
		fieldname=["name", "customer", "customer_name"],
		as_dict=True,
		order_by="creation desc"
	)

	if lease:
		return {
			"agreement_type": "Lease Agreement",
			"agreement_no": lease.name,
			"customer": lease.customer,
			"customer_name": lease.customer_name
		}

	# Check for active Rental Agreement
	rental = frappe.db.get_value(
		"Rental Agreement",
		filters={
			"vehicle": vehicle,
			"docstatus": 1,
			"agreement_status": ["in", ["Active", "Open", "Due for Return"]]
		},
		fieldname=["name", "customer", "customer_name"],
		as_dict=True,
		order_by="creation desc"
	)

	if rental:
		return {
			"agreement_type": "Rental Agreement",
			"agreement_no": rental.name,
			"customer": rental.customer,
			"customer_name": rental.customer_name
		}

	# Check for active Reservation
	reservation = frappe.db.get_value(
		"Reservation",
		filters={
			"vehicle": vehicle,
			"reservation_status": ["in", ["Confirmed", "Allocated", "Checked Out"]]
		},
		fieldname=["name", "customer", "customer_name"],
		as_dict=True,
		order_by="creation desc"
	)

	if reservation:
		return {
			"agreement_type": "Reservation",
			"agreement_no": reservation.name,
			"customer": reservation.customer,
			"customer_name": reservation.customer_name
		}

	return None


@frappe.whitelist()
def get_kanban_settings():
	"""Get status settings for Kanban board"""
	statuses = frappe.get_all(
		"Vehicle Status",
		fields=["status_name", "display_order", "color", "is_terminal", "is_available_for_booking"],
		order_by="display_order asc"
	)

	# Get transitions for each status
	for status in statuses:
		status["allowed_transitions"] = frappe.get_all(
			"Vehicle Status Transition",
			filters={"parent": status.status_name},
			fields=["target_status", "requires_reason"]
		)

	return statuses


@frappe.whitelist()
def get_kanban_vehicles(filters=None):
	"""Get vehicles for Kanban board with agreement/workshop info"""
	import json

	if filters and isinstance(filters, str):
		filters = json.loads(filters)
	filters = filters or {}

	# Get vehicles
	vehicles = frappe.get_all(
		"Vehicle",
		filters=filters,
		fields=[
			"name", "plate_no", "plate_code", "custom_plate_code", "make", "model", "year",
			"status", "branch", "body_type", "fuel_level", "odometer", "vehicle_id"
		]
	)

	# Enrich with agreement/workshop info
	for vehicle in vehicles:
		vehicle["agreement_info"] = None
		vehicle["workshop_info"] = None

		# Check for active Lease Agreement
		lease = frappe.db.get_value(
			"Lease Agreement",
			filters={
				"vehicle": vehicle["name"],
				"docstatus": 1,
				"lease_status": ["in", ["Active", "Due for Return"]]
			},
			fieldname=["name", "customer", "customer_name", "start_date", "end_date"],
			as_dict=True,
			order_by="creation desc"
		)

		if lease:
			vehicle["agreement_info"] = {
				"agreement_type": "Lease Agreement",
				"agreement_no": lease.name,
				"customer": lease.customer,
				"customer_name": lease.customer_name,
				"start_date": str(lease.start_date) if lease.start_date else None,
				"end_date": str(lease.end_date) if lease.end_date else None
			}
		else:
			# Check for active Rental Agreement
			rental = frappe.db.get_value(
				"Rental Agreement",
				filters={
					"vehicle": vehicle["name"],
					"docstatus": 1,
					"agreement_status": ["in", ["Active", "Open", "Due for Return"]]
				},
				fieldname=["name", "customer", "customer_name", "start_datetime", "end_datetime"],
				as_dict=True,
				order_by="creation desc"
			)

			if rental:
				vehicle["agreement_info"] = {
					"agreement_type": "Rental Agreement",
					"agreement_no": rental.name,
					"customer": rental.customer,
					"customer_name": rental.customer_name,
					"start_date": str(rental.start_datetime) if rental.start_datetime else None,
					"end_date": str(rental.end_datetime) if rental.end_datetime else None
				}

		# Check for workshop if status is At Garage, Under Maintenance, or Accident/Repair
		if vehicle["status"] in ["At Garage", "Under Maintenance", "Accident/Repair"]:
			# Get the latest workshop movement
			workshop_movement = frappe.db.get_value(
				"Movements",
				filters={
					"vehicle": vehicle["name"],
					"movement_type": "Workshop",
					"status": "Out Only"
				},
				fieldname=["workshop"],
				as_dict=True,
				order_by="creation desc"
			)

			if workshop_movement and workshop_movement.workshop:
				workshop_name = frappe.db.get_value("Workshop", workshop_movement.workshop, "workshop_name")
				vehicle["workshop_info"] = {
					"workshop": workshop_movement.workshop,
					"workshop_name": workshop_name or workshop_movement.workshop
				}

	return vehicles


@frappe.whitelist()
def create_draft_movement_for_kanban(vehicle, from_status, to_status, movement_type, direction,
									 agreement_type=None, agreement_no=None, customer=None):
	"""Create a draft Movement record for the Kanban modal form"""

	vehicle_doc = frappe.get_doc("Vehicle", vehicle)

	# Validate transition first
	can_change, error = VehicleStatus.can_transition(from_status, to_status)
	if not can_change:
		frappe.throw(error)

	movement = frappe.new_doc("Movements")
	movement.vehicle = vehicle
	movement.movement_type = movement_type
	movement.date = frappe.utils.today()
	movement.movement_subtype = f"Kanban: {from_status} → {to_status}"

	# Set agreement info if provided
	if agreement_type:
		movement.agreement_type = agreement_type
	if agreement_no:
		movement.agreement_no = agreement_no

	# Set direction-specific defaults
	if direction == "out":
		movement.status = "Out Only"
		movement.out_date_time = frappe.utils.now()
		movement.out_mileage = vehicle_doc.odometer
		movement.out_fuel_percentage = vehicle_doc.fuel_level
		movement.out_branch = vehicle_doc.branch
		if customer:
			movement.out_customer = customer
	elif direction == "in":
		movement.status = "Returned"
		movement.in_date_time = frappe.utils.now()
		movement.in_mileage = vehicle_doc.odometer
		movement.in_fuel_percentage = vehicle_doc.fuel_level
		movement.in_branch = vehicle_doc.branch
		if customer:
			movement.in_customer = customer

	movement.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"name": movement.name}


@frappe.whitelist()
def finalize_kanban_status_change(vehicle, to_status, movement_name):
	"""Finalize the status change after Movement form is saved in Kanban modal"""

	vehicle_doc = frappe.get_doc("Vehicle", vehicle)
	from_status = vehicle_doc.status

	# Validate transition
	can_change, error = VehicleStatus.can_transition(from_status, to_status)
	if not can_change:
		return {"success": False, "error": error}

	# Get the movement doc to extract data for vehicle update
	movement_doc = frappe.get_doc("Movements", movement_name)

	# Update vehicle status
	vehicle_doc.status = to_status

	# Update vehicle odometer and fuel from movement
	if movement_doc.status == "Out Only":
		if movement_doc.out_mileage:
			vehicle_doc.odometer = movement_doc.out_mileage
		if movement_doc.out_fuel_percentage is not None:
			vehicle_doc.fuel_level = movement_doc.out_fuel_percentage
	elif movement_doc.status == "Returned":
		if movement_doc.in_mileage:
			vehicle_doc.odometer = movement_doc.in_mileage
		if movement_doc.in_fuel_percentage is not None:
			vehicle_doc.fuel_level = movement_doc.in_fuel_percentage

	vehicle_doc.save()

	# Create status log
	frappe.get_doc({
		"doctype": "Vehicle Status Log",
		"vehicle": vehicle,
		"from_status": from_status,
		"to_status": to_status,
		"changed_at": frappe.utils.now(),
		"changed_by": frappe.session.user,
		"reason": movement_doc.movement_subtype,
		"reference_doctype": "Movements",
		"reference_name": movement_name
	}).insert(ignore_permissions=True)

	frappe.db.commit()

	return {
		"success": True,
		"message": _("Vehicle status changed from '{0}' to '{1}'").format(from_status, to_status),
		"movement": movement_name
	}
