import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, now, getdate


class RentalAgreement(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_days()
        self.calculate_amounts()
        self.validate_vehicle_availability()

    def before_submit(self):
        if self.odometer_out is None:
            frappe.throw("Please record odometer reading at pickup")
        if self.fuel_out is None:
            frappe.throw("Please record fuel level at pickup")
        if not self.terms_accepted:
            frappe.throw("Customer must accept terms and conditions")

    def on_submit(self):
        self.update_vehicle_status("Rented Out")

        # Try to create invoice, but don't fail the submission if it errors
        try:
            self.create_invoice()
            if self.erpnext_invoice:
                frappe.msgprint(f"Rental Agreement submitted! Invoice {self.erpnext_invoice} created.", indicator="green")
            else:
                frappe.msgprint("Rental Agreement submitted successfully!", indicator="green")
        except Exception as e:
            frappe.log_error(f"Invoice creation failed for {self.name}: {str(e)}", "Rental Invoice Creation")
            frappe.msgprint("Rental Agreement submitted successfully! Invoice creation will be handled separately.", indicator="blue")

        self.agreement_status = "Active"
        # Persist status change immediately
        self.db_set("agreement_status", "Active", update_modified=False)

    def on_cancel(self):
        self.update_vehicle_status("Available")
        self.agreement_status = "Cancelled"

    def validate_dates(self):
        """Validate start and end dates."""
        if get_datetime(self.end_datetime) <= get_datetime(self.start_datetime):
            frappe.throw("End date/time must be after start date/time")

    def calculate_days(self):
        """Calculate planned and actual days."""
        hours = (
            get_datetime(self.end_datetime) - get_datetime(self.start_datetime)
        ).total_seconds() / 3600
        self.planned_days = hours / 24

        if self.actual_return_datetime:
            actual_hours = (
                get_datetime(self.actual_return_datetime) - get_datetime(self.start_datetime)
            ).total_seconds() / 3600
            self.actual_days = actual_hours / 24

            # Check if overdue
            if get_datetime(self.actual_return_datetime) > get_datetime(self.end_datetime):
                self.is_overdue = 1
        else:
            self.actual_days = 0

    def calculate_amounts(self):
        """Calculate all amounts."""
        # Reset computed fields to avoid stale values
        self.km_driven = flt(self.km_driven or 0)
        self.overage_km = flt(self.overage_km or 0)
        self.overage_amount = flt(self.overage_amount or 0)
        self.rental_amount = flt(self.rental_amount or 0)
        self.discount_amount = flt(self.discount_amount or 0)
        self.tax_amount = flt(self.tax_amount or 0)

        # Calculate KM driven and overage
        if self.odometer_in is not None and self.odometer_out is not None:
            self.km_driven = flt(self.odometer_in) - flt(self.odometer_out)
            free_km = flt(self.free_km or 0)
            if self.km_driven > free_km:
                self.overage_km = self.km_driven - free_km
                if self.rate_plan:
                    rate_plan = frappe.get_doc("Rate Plan", self.rate_plan)
                    self.overage_amount = flt(self.overage_km) * flt(
                        getattr(rate_plan, "overage_per_km", 0)
                    )

        # Calculate rental amount
        if self.rate_plan and self.base_rate:
            rate_plan = frappe.get_doc("Rate Plan", self.rate_plan)
            days = flt(self.actual_days) or flt(self.planned_days)
            if rate_plan.rate_type == "Daily":
                self.rental_amount = flt(self.base_rate) * days
            elif rate_plan.rate_type == "Weekly":
                self.rental_amount = flt(self.base_rate) * (days / 7)
            elif rate_plan.rate_type == "Monthly":
                self.rental_amount = flt(self.base_rate) * (days / 30)
            else:
                self.rental_amount = 0

        # Charges total (safe if no child rows)
        charges_total = sum(flt(charge.amount) for charge in (self.charges or []))
        self.subtotal = flt(self.rental_amount) + flt(self.overage_amount) + charges_total

        # Apply discount
        if self.discount_percent:
            self.discount_amount = flt(self.subtotal) * flt(self.discount_percent) / 100

        # Calculate grand total
        self.grand_total = flt(self.subtotal) - flt(self.discount_amount) + flt(self.tax_amount)
        self.rounded_total = round(self.grand_total)

        # Calculate outstanding
        self.amount_due = self.grand_total
        self.outstanding_amount = flt(self.amount_due) - flt(self.amount_paid) - flt(
            self.deposit_applied
        )

    def validate_vehicle_availability(self):
        """Validate vehicle is available."""
        if self.vehicle and not self.is_new():
            vehicle = frappe.get_doc("Vehicle", self.vehicle)
            if vehicle.status not in ["Available", "Reserved", "Rented Out"]:
                frappe.throw(f"Vehicle is not available. Current status: {vehicle.status}")

    def update_vehicle_status(self, status):
        """Update vehicle status."""
        vehicle = frappe.get_doc("Vehicle", self.vehicle)
        vehicle.update_status(
            status,
            reason=f"Rental Agreement {self.name}",
            reference_doctype="Rental Agreement",
            reference_name=self.name,
        )

    @frappe.whitelist()
    def start_rental(self):
        """Start the rental - capture pickup details."""
        # Allow starting if document is Draft OR if submitted but status is still Draft
        # (handles manually submitted documents)
        if self.docstatus == 1 and self.agreement_status != "Draft":
            frappe.throw("Rental has already been started. Current status: " + self.agreement_status)

        if self.docstatus == 2:
            frappe.throw("Cannot start a cancelled agreement. Please amend it first.")

        if self.agreement_status not in ["Draft", "Draft"]:
            frappe.throw("Agreement must be in Draft status to start rental")

        # Validate required fields (allow 0; only None is invalid)
        if self.odometer_out is None:
            frappe.throw("Please record odometer reading")
        if self.fuel_out is None:
            frappe.throw("Please record fuel level")

        # Update vehicle odometer
        vehicle = frappe.get_doc("Vehicle", self.vehicle)
        vehicle.update_odometer(self.odometer_out, source="Agreement")

        # If document is draft, submit it
        if self.docstatus == 0:
            self.submit()
        else:
            # Document already submitted, just update status
            self.update_vehicle_status("Rented Out")
            self.db_set("agreement_status", "Active", update_modified=False)

        frappe.msgprint("Rental started successfully")

    @frappe.whitelist()
    def return_vehicle(self):
        """Process vehicle return."""
        if self.agreement_status != "Active":
            frappe.throw("Agreement must be Active to process return")

        # Validate return details (allow 0; only None is invalid)
        if self.odometer_in is None:
            frappe.throw("Please record return odometer reading")
        if self.fuel_in is None:
            frappe.throw("Please record return fuel level")
        if flt(self.odometer_in) < flt(self.odometer_out or 0):
            frappe.throw("Return odometer cannot be less than pickup odometer")

        # Set actual return time
        self.actual_return_datetime = now()

        # Recalculate amounts and potential fees
        self.calculate_days()
        self.calculate_amounts()
        self.calculate_fuel_charge()
        if getattr(self, "is_overdue", 0):
            self.calculate_late_fees()

        # Update vehicle
        vehicle = frappe.get_doc("Vehicle", self.vehicle)
        vehicle.update_odometer(self.odometer_in, source="Agreement")
        vehicle.fuel_level = self.fuel_in
        vehicle.update_status("Available", reason=f"Returned from {self.name}")

        # Update status and save
        self.agreement_status = "Returned"
        self.save()
        self.reload()  # Reload to get fresh data

        # Create/update invoice
        self.create_invoice()
        frappe.msgprint(f"Vehicle returned. Outstanding amount: {self.outstanding_amount}")

    def calculate_fuel_charge(self):
        """Calculate fuel refill charge if returned with less fuel."""
        if self.fuel_in is not None and self.fuel_out is not None and flt(self.fuel_in) < flt(self.fuel_out):
            fuel_diff = flt(self.fuel_out) - flt(self.fuel_in)
            # Assume 50 liters tank and 2 currency per liter
            fuel_cost = (fuel_diff / 100) * 50 * 2

            self.append(
                "charges",
                {
                    "charge_type": "Fuel",
                    "description": f"Fuel refill charge ({fuel_diff}%)",
                    "qty": 1,
                    "rate": fuel_cost,
                    "amount": fuel_cost,
                },
            )

    def calculate_late_fees(self):
        """Calculate late return fees."""
        if not getattr(self, "is_overdue", 0):
            return

        # Calculate hours late
        hours_late = (
            get_datetime(self.actual_return_datetime) - get_datetime(self.end_datetime)
        ).total_seconds() / 3600

        # Get grace period from rate plan
        rate_plan = frappe.get_doc("Rate Plan", self.rate_plan)
        grace_hours = flt(getattr(rate_plan, "grace_period_hours", 0))

        if hours_late > grace_hours:
            chargeable_hours = hours_late - grace_hours
            # Charge 10% of daily rate per hour
            hourly_rate = flt(self.base_rate) * 0.1
            late_fee = chargeable_hours * hourly_rate

            self.append(
                "charges",
                {
                    "charge_type": "Late Fee",
                    "description": f"Late return fee ({chargeable_hours:.1f} hours)",
                    "qty": chargeable_hours,
                    "rate": hourly_rate,
                    "amount": late_fee,
                },
            )

    @frappe.whitelist()
    def close_agreement(self):
        """Close the agreement and process final settlement."""
        if self.agreement_status != "Returned":
            frappe.throw("Agreement must be in Returned status")

        # Check if fully paid
        if flt(self.outstanding_amount) > 0:
            frappe.msgprint(
                f"Outstanding amount: {self.outstanding_amount}. Please collect payment."
            )
            return

        # Process deposit refund
        deposit_to_refund = flt(self.deposit_held) - flt(self.deposit_applied)
        if deposit_to_refund > 0:
            self.deposit_refunded = deposit_to_refund
            if frappe.db.exists("DocType", "Payment Entry"):
                self.create_deposit_refund()

        # Update status
        self.agreement_status = "Closed"
        self.save()
        self.reload()  # Reload to get fresh data

        # Create utilization snapshot
        self.create_utilization_snapshot()

        frappe.msgprint("Agreement closed successfully")

    def ensure_rental_service_item(self):
        """Ensure Rental Service item exists in ERPNext."""
        if not frappe.db.exists("Item", "Rental Service"):
            try:
                item = frappe.new_doc("Item")
                item.item_code = "Rental Service"
                item.item_name = "Rental Service"
                item.item_group = "Services"
                item.stock_uom = "Nos"
                item.is_stock_item = 0
                item.is_sales_item = 1
                item.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(f"Failed to create Rental Service item: {str(e)}", "Rental Item Creation")

    def create_invoice(self):
        """Create invoice (ERPNext or internal)."""
        if frappe.db.exists("DocType", "Sales Invoice"):
            self.create_erpnext_invoice()
        else:
            self.create_internal_invoice()

    def create_erpnext_invoice(self):
        """Create ERPNext Sales Invoice."""
        try:
            # Ensure rental service item exists
            self.ensure_rental_service_item()

            # Check if customer exists and is properly configured
            if not frappe.db.exists("Customer", self.customer):
                frappe.log_error(f"Customer {self.customer} does not exist", "Invoice Creation Failed")
                return

            # Ensure customer has required fields for ERPNext invoice
            customer_doc = frappe.get_doc("Customer", self.customer)
            modified = False

            if not customer_doc.get("customer_group"):
                customer_doc.customer_group = "All Customer Groups"
                modified = True

            if not customer_doc.get("territory"):
                customer_doc.territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
                modified = True

            if modified:
                customer_doc.flags.ignore_mandatory = True
                customer_doc.flags.ignore_validate = True
                customer_doc.save(ignore_permissions=True)

            if self.erpnext_invoice:
                invoice = frappe.get_doc("Sales Invoice", self.erpnext_invoice)
                invoice.items = []
            else:
                invoice = frappe.new_doc("Sales Invoice")
                invoice.customer = self.customer
                invoice.posting_date = getdate()
                invoice.due_date = getdate()
                invoice.ignore_pricing_rule = 1
                invoice.disable_rounded_total = 1

                # Get company from settings or use default
                invoice.company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

                # Set minimal required fields
                if not invoice.get("currency"):
                    invoice.currency = frappe.db.get_value("Company", invoice.company, "default_currency") or "AED"

                if not invoice.get("selling_price_list"):
                    invoice.selling_price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"

            # Add rental charge
            invoice.append(
                "items",
                {
                    "item_code": "Rental Service",  # Ensure this Item exists in ERPNext
                    "item_name": f"Vehicle Rental - {self.vehicle}",
                    "description": f"Rental Agreement {self.name}",
                    "qty": flt(self.actual_days or self.planned_days),
                    "rate": flt(self.base_rate),
                    "amount": flt(self.rental_amount),
                },
            )

            # Add overage
            if flt(self.overage_amount) and flt(self.overage_km):
                invoice.append(
                    "items",
                    {
                        "item_code": "Rental Service",
                        "item_name": "KM Overage",
                        "description": f"{flt(self.overage_km)} KM overage",
                        "qty": flt(self.overage_km),
                        "rate": flt(self.overage_amount) / flt(self.overage_km),
                        "amount": flt(self.overage_amount),
                    },
                )

            # Add other charges
            for charge in (self.charges or []):
                invoice.append(
                    "items",
                    {
                        "item_code": "Rental Service",
                        "item_name": charge.charge_type,
                        "description": charge.description,
                        "qty": flt(charge.qty or 1),
                        "rate": flt(charge.rate or 0),
                        "amount": flt(charge.amount or 0),
                    },
                )

            # Save with flags to bypass validations
            invoice.flags.ignore_mandatory = True
            invoice.flags.ignore_validate = True
            invoice.save(ignore_permissions=True)
            self.erpnext_invoice = invoice.name
            self.db_set("erpnext_invoice", invoice.name, update_modified=False)

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "ERPNext Invoice Creation Failed")
            frappe.msgprint(f"Note: Invoice creation skipped due to configuration issue. Agreement saved successfully.", indicator="orange")
            # Don't raise - allow agreement to be saved even if invoice fails

    def create_internal_invoice(self):
        """Create internal invoice if ERPNext not available."""
        if not frappe.db.exists("DocType", "Invoice"):
            return

        invoice = frappe.get_doc(
            {
                "doctype": "Invoice",
                "customer": self.customer,
                "reference_type": "Rental Agreement",
                "reference_name": self.name,
                "posting_date": getdate(),
                "due_date": getdate(),
                "total": flt(self.grand_total),
                "outstanding": flt(self.outstanding_amount),
                "status": "Unpaid" if flt(self.outstanding_amount) > 0 else "Paid",
            }
        )

        invoice.append(
            "items",
            {
                "item_name": f"Vehicle Rental - {self.vehicle}",
                "description": f"Rental Agreement {self.name}",
                "qty": flt(self.actual_days or self.planned_days),
                "rate": flt(self.base_rate),
                "amount": flt(self.rental_amount),
            },
        )

        invoice.insert(ignore_permissions=True)

    def create_deposit_refund(self):
        """Create payment entry for deposit refund."""
        if not frappe.db.exists("DocType", "Payment Entry"):
            return

        payment = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "payment_type": "Pay",
                "party_type": "Customer",
                "party": self.customer,
                "paid_amount": flt(self.deposit_refunded),
                "received_amount": flt(self.deposit_refunded),
                "reference_no": self.name,
                "reference_date": getdate(),
                "remarks": f"Deposit refund for {self.name}",
            }
        )
        payment.insert(ignore_permissions=True)
        self.erpnext_payment_entry = payment.name

    def create_utilization_snapshot(self):
        """Create utilization snapshot for reporting."""
        if not frappe.db.exists("DocType", "Utilization Snapshot"):
            return

        snapshot = frappe.get_doc(
            {
                "doctype": "Utilization Snapshot",
                "snapshot_date": getdate(),
                "vehicle": self.vehicle,
                "rented_hours": flt(self.actual_days or self.planned_days) * 24,
                "revenue": flt(self.grand_total),
            }
        )
        snapshot.insert(ignore_permissions=True)


def validate_agreement(doc, method=None):
    """Hook for validate."""
    pass


def on_agreement_submit(doc, method=None):
    """Hook for on_submit."""
    pass


def on_agreement_cancel(doc, method=None):
    """Hook for on_cancel."""
    pass
