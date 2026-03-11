# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import now_datetime, get_datetime

class Movements(Document):
	def validate(self):
		"""Validate and auto-calculate fields"""
		self.validate_replacement_workflow()
		self.validate_workshop_invoice()
		self.calculate_distance_traveled()
		self.auto_detect_damage_states()
		self.update_status()
		self.calculate_condition_delta()

	def validate_replacement_workflow(self):
		"""Validate replacement workflow requirements"""
		# Auto-set is_replacement for replacement movement types
		if self.movement_type and 'Replacement' in self.movement_type:
			self.is_replacement = 1

		# Validate replacement vehicle is set for "Replacement - Vehicle Out"
		if self.movement_type == 'Replacement - Vehicle Out':
			if not self.replacement_vehicle:
				frappe.throw(_("Replacement Vehicle is mandatory for 'Replacement - Vehicle Out' movement type"))

			# The replacement vehicle should be different from the main vehicle
			if self.replacement_vehicle == self.vehicle:
				frappe.throw(_("Replacement Vehicle must be different from the main Vehicle"))

	def validate_workshop_invoice(self):
		"""Validate workshop movements have Purchase Invoice when returned"""
		if self.movement_type == 'Workshop':
			# Only require Purchase Invoice when vehicle is returned (IN date/time is set)
			if self.in_date_time and not self.workshop_purchase_invoice:
				frappe.throw(
					_("Workshop Purchase Invoice is mandatory when returning a vehicle from workshop. "
					  "Please create a Purchase Invoice for the workshop repair/service and link it here.")
				)

	def auto_detect_damage_states(self):
		"""
		Auto-detect damage states by comparing IN damages with OUT damages from the same movement.
		- 'existing': Damage was already present in OUT inspection with same severity
		- 'worsened': Damage exists in OUT but severity increased
		- 'new': Damage not found in OUT inspection
		"""
		if not self.in_vehicle_damage_logs:
			return

		# Map severity to numeric values for comparison
		severity_map = {
			'Minor': 1,
			'Moderate': 2,
			'Severe': 3,
			'Critical': 4
		}

		# Get OUT damage logs from this movement
		out_damages = self.out_vehicle_damage_logs or []

		# Debug: Log comparison details
		frappe.logger().debug(f"Comparing {len(self.in_vehicle_damage_logs)} IN damages with {len(out_damages)} OUT damages")

		# Compare IN damages with OUT damages
		for in_damage in self.in_vehicle_damage_logs:
			damage_state = 'new'  # Default to new

			# Look for matching damage in OUT inspection
			for out_damage in out_damages:
				frappe.logger().debug(f"Comparing IN: {in_damage.zone}/{in_damage.damage_type} with OUT: {out_damage.zone}/{out_damage.damage_type}")

				if (in_damage.zone == out_damage.zone and
					in_damage.damage_type == out_damage.damage_type):

					# Found matching damage - check severity
					in_severity = severity_map.get(in_damage.severity, 1)
					out_severity = severity_map.get(out_damage.severity, 1)

					frappe.logger().debug(f"Match found! IN severity: {in_damage.severity} ({in_severity}), OUT severity: {out_damage.severity} ({out_severity})")

					if in_severity > out_severity:
						damage_state = 'worsened'
					else:
						damage_state = 'existing'
					break

			frappe.logger().debug(f"Setting damage state for {in_damage.zone}/{in_damage.damage_type}: {damage_state}")
			in_damage.damage_state = damage_state

	def calculate_distance_traveled(self):
		"""Auto-calculate distance based on mileage difference"""
		if self.in_mileage and self.out_mileage:
			distance = self.in_mileage - self.out_mileage
			if distance >= 0:
				self.distance_traveled = distance
			else:
				frappe.msgprint(_("Warning: IN mileage is less than OUT mileage"), indicator="orange")

	def update_status(self):
		"""Auto-update status based on movement data"""
		if not self.status or self.status == "Draft":
			# Check for critical damage flags in both OUT and IN
			out_damages = self.out_vehicle_damage_logs or []
			in_damages = self.in_vehicle_damage_logs or []

			has_critical_damage = any(
				d.severity == "Critical" for d in list(out_damages) + list(in_damages)
			)

			if has_critical_damage:
				self.status = "Issue Flagged"
			elif self.out_date_time and self.in_date_time:
				self.status = "Returned"
			elif self.out_date_time:
				self.status = "Out Only"
			else:
				self.status = "Draft"

	def calculate_condition_delta(self):
		"""Compare OUT vs IN condition and generate delta summary"""
		delta_items = []

		# Fuel level comparison
		if self.out_fuel_percentage is not None and self.in_fuel_percentage is not None:
			fuel_diff = self.in_fuel_percentage - self.out_fuel_percentage
			if fuel_diff < 0:
				delta_items.append(f"⚠️ Fuel consumed: {abs(fuel_diff)}%")
			elif fuel_diff > 0:
				delta_items.append(f"✓ Fuel added: {fuel_diff}%")

		# Mileage/distance check
		if self.distance_traveled:
			delta_items.append(f"📏 Distance: {self.distance_traveled} km")

		# Damage analysis - Compare OUT vs IN
		out_damages = self.out_vehicle_damage_logs or []
		in_damages = self.in_vehicle_damage_logs or []

		if out_damages or in_damages:
			# Show OUT damage count
			out_count = len(out_damages)
			in_count = len(in_damages)
			delta_items.append(f"📋 Damages: OUT {out_count} → IN {in_count}")

			# Count IN damages by state
			if in_damages:
				state_counts = {'new': 0, 'existing': 0, 'worsened': 0}
				for damage in in_damages:
					state = damage.damage_state or 'new'
					state_counts[state] = state_counts.get(state, 0) + 1

				damage_parts = []
				if state_counts['new'] > 0:
					damage_parts.append(f"🔴 {state_counts['new']} New")
				if state_counts['worsened'] > 0:
					damage_parts.append(f"🟡 {state_counts['worsened']} Worsened")
				if state_counts['existing'] > 0:
					damage_parts.append(f"🟢 {state_counts['existing']} Existing")

				if damage_parts:
					delta_items.append(f"   └─ {', '.join(damage_parts)}")

			# Flag critical damages (from both OUT and IN)
			all_damages = list(out_damages) + list(in_damages)
			critical_damages = [d for d in all_damages if d.severity == "Critical"]
			if critical_damages:
				for damage in critical_damages:
					delta_items.append(f"❌ CRITICAL: {damage.zone} - {damage.damage_type}")

		# Check notes for tags
		out_tags = extract_tags(self.out_notes or "")
		in_tags = extract_tags(self.in_notes or "")

		if out_tags or in_tags:
			if out_tags:
				delta_items.append(f"OUT Tags: {', '.join(out_tags)}")
			if in_tags:
				delta_items.append(f"IN Tags: {', '.join(in_tags)}")

		# Set condition delta
		if delta_items:
			self.condition_delta = "\n".join(delta_items)
		else:
			self.condition_delta = "No significant changes detected"

	def before_submit(self):
		"""Validation before submission"""
		if not self.in_date_time:
			frappe.throw(_("Cannot submit movement without IN date/time"))

		if self.status == "Issue Flagged":
			frappe.msgprint(
				_("Warning: This movement has flagged issues. Please review before submission."),
				indicator="orange",
				alert=True
			)


def extract_tags(text):
	"""Extract tags from notes field (e.g., [Dirty], [Fuel Low])"""
	import re
	if not text:
		return []
	return re.findall(r'\[(.*?)\]', text)
