import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_datetime


class RentalQuotation(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_days()
        self.calculate_amounts()

    def validate_dates(self):
        """Validate start and end dates."""
        if get_datetime(self.end_datetime) <= get_datetime(self.start_datetime):
            frappe.throw("End date/time must be after start date/time")

        # Auto-set valid_until if not set (7 days from quotation date)
        if not self.valid_until:
            from frappe.utils import add_days, getdate
            self.valid_until = add_days(self.quotation_date, 7)

    def calculate_days(self):
        """Calculate planned days."""
        hours = (
            get_datetime(self.end_datetime) - get_datetime(self.start_datetime)
        ).total_seconds() / 3600
        self.planned_days = hours / 24

    def calculate_amounts(self):
        """Calculate all amounts."""
        # Calculate rental amount
        if self.rate_plan and self.base_rate:
            rate_plan = frappe.get_doc("Rate Plan", self.rate_plan)
            days = flt(self.planned_days)
            if rate_plan.rate_type == "Daily":
                self.rental_amount = flt(self.base_rate) * days
            elif rate_plan.rate_type == "Weekly":
                self.rental_amount = flt(self.base_rate) * (days / 7)
            elif rate_plan.rate_type == "Monthly":
                self.rental_amount = flt(self.base_rate) * (days / 30)
            else:
                self.rental_amount = 0

        # Calculate extras total
        extras_total = sum(flt(extra.amount) for extra in (self.extras or []))
        self.extras_total = extras_total

        # Calculate grand total
        self.grand_total = flt(self.rental_amount) + flt(self.extras_total)

    @frappe.whitelist()
    def generate_rental_agreement(self):
        """Generate Rental Agreement from this quotation."""
        if self.rental_agreement:
            frappe.throw(f"Rental Agreement {self.rental_agreement} already generated from this quotation")

        if self.quotation_status not in ["Sent", "Draft"]:
            if self.quotation_status == "Accepted":
                frappe.throw("This quotation has already been accepted and an agreement generated")
            else:
                frappe.throw(f"Cannot generate agreement from {self.quotation_status} quotation")

        # Create rental agreement
        agreement = frappe.get_doc({
            "doctype": "Rental Agreement",
            "quotation": self.name,
            "customer": self.customer,
            "driver": self.driver,
            "vehicle": self.vehicle,
            "start_datetime": self.start_datetime,
            "end_datetime": self.end_datetime,
            "branch": self.branch,
            "return_branch": self.return_branch,
            "rate_plan": self.rate_plan,
            "agreement_status": "Draft"
        })

        # Copy extras
        for extra in (self.extras or []):
            agreement.append("charges", {
                "charge_type": extra.extra_name,
                "description": extra.description,
                "qty": extra.qty,
                "rate": extra.rate,
                "amount": extra.amount
            })

        agreement.insert()

        # Update quotation
        self.quotation_status = "Accepted"
        self.rental_agreement = agreement.name
        self.generated_on = frappe.utils.now()
        self.save()

        frappe.msgprint(f"Rental Agreement {agreement.name} created successfully")

        return {
            "success": True,
            "agreement": agreement.name
        }
