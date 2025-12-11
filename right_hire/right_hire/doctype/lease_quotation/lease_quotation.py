import frappe
from frappe.model.document import Document
from frappe.utils import flt, add_months, getdate


class LeaseQuotation(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_end_date()
        self.calculate_amounts()

    def validate_dates(self):
        """Validate dates."""
        # Auto-set valid_until if not set (7 days from quotation date)
        if not self.valid_until:
            from frappe.utils import add_days
            self.valid_until = add_days(self.quotation_date, 7)

    def calculate_end_date(self):
        """Calculate lease end date."""
        if self.start_date and self.lease_duration_months:
            self.end_date = add_months(self.start_date, self.lease_duration_months)

    def calculate_amounts(self):
        """Calculate total lease amount."""
        if self.monthly_rate and self.lease_duration_months:
            self.total_amount = flt(self.monthly_rate) * flt(self.lease_duration_months)

    @frappe.whitelist()
    def generate_lease_contract(self):
        """Generate Lease Contract from this quotation."""
        if self.lease_contract:
            frappe.throw(f"Lease Contract {self.lease_contract} already generated from this quotation")

        if self.quotation_status not in ["Sent", "Draft"]:
            if self.quotation_status == "Accepted":
                frappe.throw("This quotation has already been accepted and a contract generated")
            else:
                frappe.throw(f"Cannot generate contract from {self.quotation_status} quotation")

        # Create lease contract
        contract = frappe.get_doc({
            "doctype": "Lease Contract",
            "quotation": self.name,
            "customer": self.customer,
            "driver": self.driver,
            "vehicle": self.vehicle,
            "start_date": self.start_date,
            "lease_duration_months": self.lease_duration_months,
            "end_date": self.end_date,
            "branch": self.branch,
            "rate_plan": self.rate_plan,
            "monthly_rate": self.monthly_rate,
            "deposit_amount": self.deposit_amount,
            "allowed_km_per_year": self.allowed_km_per_year,
            "maintenance_included": self.maintenance_included,
            "insurance_included": self.insurance_included,
            "contract_status": "Draft"
        })

        contract.insert()

        # Update quotation
        self.quotation_status = "Accepted"
        self.lease_contract = contract.name
        self.generated_on = frappe.utils.now()
        self.save()

        frappe.msgprint(f"Lease Contract {contract.name} created successfully")

        return {
            "success": True,
            "contract": contract.name
        }
