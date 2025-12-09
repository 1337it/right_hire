# Copyright (c) 2024, Tridz Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, date_diff, add_months, getdate
from dateutil.relativedelta import relativedelta


class LeasetoOwn(Document):
    def validate(self):
        self.calculate_lease_duration()
        self.calculate_totals()
        self.set_vehicle_details()

    def before_submit(self):
        if not self.start_date:
            frappe.throw("Start Date is required")
        if not self.end_date:
            frappe.throw("End Date is required")

    def on_submit(self):
        self.contract_status = "Active"
        self.update_vehicle_status()
        self.db_set("contract_status", "Active", update_modified=False)

    def on_cancel(self):
        self.contract_status = "Cancelled"
        self.update_vehicle_status(cancel=True)

    def calculate_lease_duration(self):
        """Calculate lease duration in months"""
        if self.start_date and self.end_date:
            start = getdate(self.start_date)
            end = getdate(self.end_date)
            delta = relativedelta(end, start)
            self.lease_duration_months = delta.years * 12 + delta.months

    def calculate_totals(self):
        """Calculate total amount and outstanding"""
        if self.down_payment and self.monthly_payment and self.lease_duration_months:
            self.total_amount = flt(self.down_payment) + (flt(self.monthly_payment) * flt(self.lease_duration_months))

        # Calculate payments remaining
        if self.amount_paid and self.monthly_payment:
            payments_made = (flt(self.amount_paid) - flt(self.down_payment)) / flt(self.monthly_payment)
            self.payments_remaining = max(0, flt(self.lease_duration_months) - int(payments_made))

        # Calculate outstanding
        self.outstanding_amount = flt(self.total_amount) - flt(self.amount_paid)

        # Check if eligible for buyout
        if self.buyout_option_date and getdate() >= getdate(self.buyout_option_date):
            if self.transfer_status == "Pending":
                self.transfer_status = "Eligible"

    def set_vehicle_details(self):
        """Set vehicle details from vehicle doctype"""
        if self.vehicle:
            vehicle = frappe.get_doc("Vehicle", self.vehicle)
            self.vehicle_details = f"{vehicle.make} {vehicle.model} {vehicle.year}"
            self.plate_no = f"{vehicle.custom_plate_code}-{vehicle.plate_no}"
            if not self.vehicle_estimated_value:
                self.vehicle_estimated_value = vehicle.current_book_value

    def update_vehicle_status(self, cancel=False):
        """Update vehicle status"""
        if self.vehicle:
            vehicle = frappe.get_doc("Vehicle", self.vehicle)
            if cancel:
                vehicle.update_status("Available", reason=f"Lease to Own {self.name} cancelled")
            else:
                vehicle.update_status("Leased", reason=f"Leased to Own under {self.name}")

    @frappe.whitelist()
    def transfer_ownership(self):
        """Process ownership transfer"""
        if self.transfer_status != "Eligible":
            frappe.throw("Contract not eligible for ownership transfer yet")

        if self.outstanding_amount > 0:
            frappe.throw(f"Outstanding amount of {self.outstanding_amount} must be paid before ownership transfer")

        # Update status
        self.transfer_status = "Completed"
        self.contract_status = "Ownership Transferred"
        self.save()

        # Update vehicle
        vehicle = frappe.get_doc("Vehicle", self.vehicle)
        vehicle.update_status("Sold", reason=f"Ownership transferred under Lease to Own {self.name}")

        frappe.msgprint(f"Ownership transferred successfully for {self.vehicle}")
        return {"success": True}

    @frappe.whitelist()
    def record_payment(self, amount, payment_date=None):
        """Record a payment"""
        amount = flt(amount)
        if amount <= 0:
            frappe.throw("Payment amount must be greater than zero")

        self.amount_paid = flt(self.amount_paid) + amount
        self.calculate_totals()
        self.save()

        frappe.msgprint(f"Payment of {amount} recorded. Outstanding: {self.outstanding_amount}")
        return {"success": True, "outstanding": self.outstanding_amount}
