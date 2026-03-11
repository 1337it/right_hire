# Copyright (c) 2026, Tridz Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json

class VehicleConditionImage(Document):
	def validate(self):
		# Parse and validate damage coordinates if provided
		if self.damage_coordinates:
			try:
				coords = json.loads(self.damage_coordinates)
				# Validate coordinate structure
				if not isinstance(coords, dict):
					frappe.throw("Damage coordinates must be a valid JSON object")
			except json.JSONDecodeError:
				frappe.throw("Invalid damage coordinates format")
