# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TrafficFine(Document):
	def before_save(self):
		# Auto-link to active contract/agreement for the vehicle
		if not self.linked_contract and not self.linked_agreement:
			self.auto_link_contract()

	def auto_link_contract(self):
		"""Auto-link to active contract or agreement based on fine date"""
		if not self.vehicle or not self.fine_date:
			return

		# Parse fine date (format: "02 May 2025")
		try:
			from datetime import datetime
			fine_date = datetime.strptime(self.fine_date, '%d %b %Y').date()
		except:
			frappe.log_error(f"Could not parse fine date: {self.fine_date}", "Traffic Fine Auto-Link")
			return

		# Check for active Lease Contract on the fine date
		lease_contract = frappe.db.get_value(
			"Lease Contract",
			{
				"vehicle": self.vehicle,
				"start_date": ["<=", fine_date],
				"end_date": [">=", fine_date],
				"docstatus": 1
			},
			"name"
		)

		if lease_contract:
			self.linked_contract = lease_contract
			return

		# Check for active Rental Agreement on the fine date
		rental_agreement = frappe.db.get_value(
			"Rental Agreement",
			{
				"vehicle": self.vehicle,
				"start_date": ["<=", fine_date],
				"end_date": [">=", fine_date],
				"docstatus": 1
			},
			"name"
		)

		if rental_agreement:
			self.linked_agreement = rental_agreement
