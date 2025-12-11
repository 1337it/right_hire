import frappe
from frappe.model.document import Document
from frappe.utils import flt, add_months


class LeasetoOwnQuotation(Document):
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
        """Calculate contract end date."""
        if self.start_date and self.contract_duration_months:
            self.end_date = add_months(self.start_date, self.contract_duration_months)

    def calculate_amounts(self):
        """Calculate payment structure."""
        # Calculate total amount from monthly payments
        if self.monthly_payment and self.contract_duration_months:
            self.number_of_payments = self.contract_duration_months
            total_monthly = flt(self.monthly_payment) * flt(self.contract_duration_months)
            self.total_amount = total_monthly + flt(self.down_payment) + flt(self.final_payment)

        # Calculate financed amount
        if self.total_amount and self.down_payment:
            self.financed_amount = flt(self.total_amount) - flt(self.down_payment)

    @frappe.whitelist()
    def generate_lease_to_own(self):
        """Generate Lease to Own contract from this quotation."""
        if self.lease_to_own:
            frappe.throw(f"Lease to Own Contract {self.lease_to_own} already generated from this quotation")

        if self.quotation_status not in ["Sent", "Draft"]:
            if self.quotation_status == "Accepted":
                frappe.throw("This quotation has already been accepted and a contract generated")
            else:
                frappe.throw(f"Cannot generate contract from {self.quotation_status} quotation")

        # Create lease to own contract
        contract = frappe.get_doc({
            "doctype": "Lease to Own",
            "quotation": self.name,
            "customer": self.customer,
            "driver": self.driver,
            "vehicle": self.vehicle,
            "start_date": self.start_date,
            "contract_duration_months": self.contract_duration_months,
            "end_date": self.end_date,
            "branch": self.branch,
            "vehicle_value": self.vehicle_value,
            "total_amount": self.total_amount,
            "down_payment": self.down_payment,
            "monthly_payment": self.monthly_payment,
            "final_payment": self.final_payment,
            "allowed_km_per_year": self.allowed_km_per_year,
            "contract_status": "Draft"
        })

        contract.insert()

        # Update quotation
        self.quotation_status = "Accepted"
        self.lease_to_own = contract.name
        self.generated_on = frappe.utils.now()
        self.save()

        frappe.msgprint(f"Lease to Own Contract {contract.name} created successfully")

        return {
            "success": True,
            "contract": contract.name
        }
