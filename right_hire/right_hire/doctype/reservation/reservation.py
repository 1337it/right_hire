import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, date_diff, flt, add_days


class Reservation(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_rental_days()
        self.calculate_amounts()
        self.validate_customer()

    def before_submit(self):
        self.check_conflicts()
        if self.allocation_mode == "Smart" and not self.vehicle:
            self.allocate_vehicle_smart()

    def validate_dates(self):
        """Validate pickup and return dates."""
        if get_datetime(self.return_datetime) <= get_datetime(self.pickup_datetime):
            frappe.throw("Return date/time must be after pickup date/time")

        # Disallow past pickups
        if get_datetime(self.pickup_datetime) < get_datetime():
            frappe.throw("Pickup date/time cannot be in the past")

    def calculate_rental_days(self):
        """Calculate rental days (fractional)."""
        hours = (
            get_datetime(self.return_datetime) - get_datetime(self.pickup_datetime)
        ).total_seconds() / 3600
        self.rental_days = hours / 24

    def calculate_amounts(self):
        """Calculate rental amounts."""
        if not self.rate_plan:
            return

        rate_plan = frappe.get_doc("Rate Plan", self.rate_plan)

        # Base rental amount
        if rate_plan.rate_type == "Daily":
            self.rental_amount = flt(self.base_rate) * flt(self.rental_days)
        elif rate_plan.rate_type == "Weekly":
            weeks = flt(self.rental_days) / 7
            self.rental_amount = flt(self.base_rate) * weeks
        elif rate_plan.rate_type == "Monthly":
            months = flt(self.rental_days) / 30
            self.rental_amount = flt(self.base_rate) * months
        else:
            self.rental_amount = 0

        # Extras total (safe if no child rows)
        self.extras_total = sum(flt(extra.amount) for extra in (self.extras or []))

        # Grand total
        self.grand_total = flt(self.rental_amount) + flt(self.extras_total)

    def validate_customer(self):
        """Validate customer eligibility."""
        customer = frappe.get_doc("Customer", self.customer)

        if getattr(customer, "is_blacklisted", 0):
            frappe.throw(f"Customer is blacklisted: {customer.blacklist_reason}")

        # Check license expiry for individual customers
        if customer.customer_type == "Individual" and customer.license_expiry:
            if getdate(customer.license_expiry) < getdate(self.pickup_datetime):
                frappe.throw("Customer's driving license will be expired at pickup time")

        # Check driver if provided
        if self.driver:
            driver = frappe.get_doc("Driver", self.driver)
            if getattr(driver, "is_blacklisted", 0):
                frappe.throw(f"Driver is blacklisted: {driver.blacklist_reason}")
            if driver.license_expiry and getdate(driver.license_expiry) < getdate(
                self.pickup_datetime
            ):
                frappe.throw("Driver's license will be expired at pickup time")

    def check_conflicts(self):
        """Check for vehicle conflicts."""
        if not self.vehicle:
            return

        vehicle = frappe.get_doc("Vehicle", self.vehicle)
        if not vehicle.check_availability(self.pickup_datetime, self.return_datetime):
            frappe.throw(
                f"Vehicle {self.vehicle} is not available for the selected period"
            )

    def allocate_vehicle_smart(self):
        """Smart vehicle allocation based on availability and preferences."""
        filters = {"status": "Available", "branch": self.branch}

        if self.preferred_make:
            filters["make"] = self.preferred_make
        if self.preferred_model:
            filters["model"] = self.preferred_model

        available_vehicles = frappe.get_all("Vehicle", filters=filters, pluck="name")

        # Pick the first available vehicle for the period
        for vehicle_name in available_vehicles:
            vehicle = frappe.get_doc("Vehicle", vehicle_name)
            if vehicle.check_availability(self.pickup_datetime, self.return_datetime):
                self.vehicle = vehicle_name
                return

        frappe.throw("No available vehicles found matching criteria")

    @frappe.whitelist()
    def convert_to_agreement(self):
        """Convert reservation to rental agreement."""
        if self.reservation_status == "Converted":
            frappe.throw("Reservation already converted")

        if not self.vehicle:
            frappe.throw("Please allocate a vehicle before converting")

        agreement = frappe.get_doc(
            {
                "doctype": "Rental Agreement",
                "reservation": self.name,
                "customer": self.customer,
                "driver": self.driver,
                "vehicle": self.vehicle,
                "branch": self.branch,
                "return_branch": self.return_branch or self.branch,
                "start_datetime": self.pickup_datetime,
                "end_datetime": self.return_datetime,
                "rate_plan": self.rate_plan,
                "base_rate": self.base_rate,
                "deposit_held": self.deposit,
                "agreement_status": "Draft",
            }
        )

        # Copy extras
        for extra in (self.extras or []):
            agreement.append(
                "charges",
                {
                    "charge_type": "Extra",
                    "description": extra.item,
                    "qty": extra.qty,
                    "rate": extra.rate,
                    "amount": extra.amount,
                },
            )

        agreement.insert()

        # Update reservation
        self.reservation_status = "Converted"
        self.rental_agreement = agreement.name
        self.converted_on = frappe.utils.now()
        self.save()

        frappe.msgprint(f"Rental Agreement {agreement.name} created successfully")
        return agreement.name

    @frappe.whitelist()
    def suggest_vehicles(self):
        """Suggest best available vehicles."""
        filters = {"status": "Available", "branch": self.branch, "availability_status": 1}

        # Placeholder for category-based filtering if you add a custom field on Vehicle
        if self.preferred_category:
            pass

        vehicles = frappe.get_all(
            "Vehicle",
            filters=filters,
            fields=["name", "make", "model", "year", "plate_no", "odometer"],
        )

        available = []
        for v in vehicles:
            vehicle = frappe.get_doc("Vehicle", v.name)
            if vehicle.check_availability(self.pickup_datetime, self.return_datetime):
                available.append(v)

        return available


def validate_reservation(doc, method=None):
    """Hook for validate."""
    pass


def check_conflicts(doc, method=None):
    """Hook to check conflicts."""
    pass
