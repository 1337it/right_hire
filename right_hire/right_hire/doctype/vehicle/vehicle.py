import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class Vehicle(Document):
    def validate(self):
        self.validate_basic_details()
        self.update_availability_status()
        self.calculate_book_value()
        self.update_plate_art()

    def validate_basic_details(self):
        """Validate basic vehicle details."""
        if self.year and self.year > int(nowdate()[:4]) + 1:
            frappe.throw("Year cannot be in the future")

        if self.odometer and flt(self.odometer) < 0:
            frappe.throw("Odometer cannot be negative")

    def update_availability_status(self):
        """Update availability based on status."""
        unavailable_statuses = [
            "Rented Out",
            "Reserved",
            "Leased",
            "Under Maintenance",
            "Accident/Repair",
            "Deactivated",
            "Custody",
        ]
        self.availability_status = 0 if self.status in unavailable_statuses else 1

    def calculate_book_value(self):
        """Calculate current book value based on depreciation."""
        if not self.purchase_cost or not self.purchase_date:
            return

        if self.depreciation_method == "Straight Line" and self.depreciation_rate:
            years_owned = (getdate() - getdate(self.purchase_date)).days / 365.25
            depreciation = (
                flt(self.purchase_cost)
                * flt(self.depreciation_rate)
                / 100
                * years_owned
            )
            self.current_book_value = max(0, flt(self.purchase_cost) - depreciation)

    def update_plate_art(self):
        """Update custom_plate_art when plate_code or plate_no changes."""
        if self.has_value_changed("plate_code") or self.has_value_changed("plate_no"):
            # Build plate art from plate_no and plate_code
            plate_code = self.plate_code or ""
            plate_no = self.plate_no or ""

            if plate_code and plate_no:
                self.custom_plate_art = f"{plate_code} {plate_no}"
            elif plate_no:
                self.custom_plate_art = plate_no
            elif plate_code:
                self.custom_plate_art = plate_code
            else:
                self.custom_plate_art = ""

    def update_odometer(self, reading, source="Manual"):
        """Update odometer reading."""
        if flt(reading) < flt(self.odometer or 0):
            frappe.throw("New odometer reading cannot be less than current reading")

        self.odometer = reading

        # Log the reading
        self.append(
            "odometer_logs",
            {"reading": reading, "logged_at": frappe.utils.now(), "source": source},
        )

        self.save()

    def add_damage_log(self, description, severity, estimated_cost=0, photos=None):
        """Add a damage log entry."""
        self.append(
            "damage_logs",
            {
                "description": description,
                "severity": severity,
                "estimated_cost": estimated_cost,
                "logged_at": frappe.utils.now(),
            },
        )
        self.save()

    def update_status(self, new_status, reason=None, reference_doctype=None, reference_name=None, skip_validation=False):
        """Update vehicle status and log the change."""
        old_status = self.status

        # Validate transition if Vehicle Status records exist
        if not skip_validation and frappe.db.exists("Vehicle Status", old_status):
            from right_hire.right_hire.doctype.vehicle_status.vehicle_status import VehicleStatus
            can_change, error = VehicleStatus.can_transition(old_status, new_status)
            if not can_change:
                frappe.throw(error)

            # Check if reason is required
            try:
                status_doc = frappe.get_doc("Vehicle Status", old_status)
                for t in status_doc.allowed_transitions:
                    if t.target_status == new_status and t.requires_reason and not reason:
                        frappe.throw("Reason is required for this status change")
                        break
            except frappe.DoesNotExistError:
                pass

        self.status = new_status
        self.save()

        # Create status log
        log = frappe.get_doc(
            {
                "doctype": "Vehicle Status Log",
                "vehicle": self.name,
                "from_status": old_status,
                "to_status": new_status,
                "reason": reason,
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "changed_at": frappe.utils.now(),
                "changed_by": frappe.session.user,
            }
        )
        log.insert(ignore_permissions=True)

    def check_availability(self, start_datetime, end_datetime):
        """Check if vehicle is available for given period."""
        if not self.availability_status:
            return False

        # Check for overlapping reservations
        overlapping = frappe.db.sql(
            """
            SELECT name
            FROM `tabReservation`
            WHERE vehicle = %s
              AND reservation_status NOT IN ('Cancelled', 'Expired')
              AND (
                    (pickup_datetime <= %s AND return_datetime >= %s)
                 OR (pickup_datetime <= %s AND return_datetime >= %s)
                 OR (pickup_datetime >= %s AND return_datetime <= %s)
              )
            """,
            (
                self.name,
                start_datetime,
                start_datetime,
                end_datetime,
                end_datetime,
                start_datetime,
                end_datetime,
            ),
        )

        if overlapping:
            return False

        # Check for overlapping agreements
        overlapping_agreements = frappe.db.sql(
            """
            SELECT name
            FROM `tabRental Agreement`
            WHERE vehicle = %s
              AND agreement_status NOT IN ('Cancelled', 'Closed')
              AND (
                    (start_datetime <= %s AND end_datetime >= %s)
                 OR (start_datetime <= %s AND end_datetime >= %s)
                 OR (start_datetime >= %s AND end_datetime <= %s)
              )
            """,
            (
                self.name,
                start_datetime,
                start_datetime,
                end_datetime,
                end_datetime,
                start_datetime,
                end_datetime,
            ),
        )

        if overlapping_agreements:
            return False

        return True

    @frappe.whitelist()
    def create_purchase_invoice(self):
        """Create Purchase Invoice for vehicle purchase"""
        if not self.purchase_cost or not self.purchase_date:
            frappe.throw("Purchase cost and date are required")

        if not frappe.db.exists("DocType", "Purchase Invoice"):
            frappe.throw("ERPNext Purchase Invoice not available")

        # Check if already created
        existing = frappe.db.get_value(
            "Purchase Invoice",
            {"vehicle": self.name, "expense_type": "Vehicle Purchase", "docstatus": 1},
            "name"
        )

        if existing:
            frappe.msgprint(f"Purchase Invoice {existing} already exists for this vehicle")
            return existing

        # Create Purchase Invoice
        pi = frappe.new_doc("Purchase Invoice")

        # Set supplier (create default if doesn't exist)
        supplier = self.get_or_create_supplier()
        pi.supplier = supplier

        pi.posting_date = getdate(self.purchase_date)
        pi.due_date = getdate(self.purchase_date)

        # Get company
        pi.company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

        # Set custom fields
        pi.vehicle = self.name
        pi.expense_type = "Vehicle Purchase"
        pi.odometer_reading = flt(self.odometer or 0)

        # Add vehicle as asset item
        pi.append("items", {
            "item_code": self.get_or_create_vehicle_item(),
            "item_name": f"{self.make} {self.model} - {self.plate_no}",
            "description": f"Vehicle Purchase - {self.vehicle_id}",
            "qty": 1,
            "rate": flt(self.purchase_cost),
            "amount": flt(self.purchase_cost),
            "expense_account": self.get_vehicle_asset_account(pi.company),
        })

        # Save and submit
        pi.flags.ignore_mandatory = True
        pi.flags.ignore_validate = True
        pi.save(ignore_permissions=True)
        pi.submit()

        frappe.msgprint(f"Purchase Invoice {pi.name} created", indicator="green")
        return pi.name

    def get_or_create_supplier(self):
        """Get or create default supplier for vehicle purchases"""
        # Use make as supplier name or create "Vehicle Suppliers"
        supplier_name = "Vehicle Suppliers"

        if not frappe.db.exists("Supplier", supplier_name):
            supplier = frappe.new_doc("Supplier")
            supplier.supplier_name = supplier_name
            supplier.supplier_group = "All Supplier Groups"
            supplier.supplier_type = "Company"
            supplier.insert(ignore_permissions=True)

        return supplier_name

    def get_or_create_vehicle_item(self):
        """Get or create Item for vehicle asset"""
        item_code = "Vehicle Asset"

        if not frappe.db.exists("Item", item_code):
            item = frappe.new_doc("Item")
            item.item_code = item_code
            item.item_name = "Vehicle Asset"
            item.item_group = "All Item Groups"
            item.stock_uom = "Nos"
            item.is_stock_item = 0
            item.is_fixed_asset = 1
            item.insert(ignore_permissions=True)

        return item_code

    def get_vehicle_asset_account(self, company):
        """Get vehicle asset account based on body type"""
        from right_hire.setup.accounts import get_account

        account_map = {
            "Sedan": "Rental Fleet - Sedans",
            "SUV": "Rental Fleet - SUVs",
            "Luxury": "Rental Fleet - Luxury",
            "Commercial": "Rental Fleet - Commercial"
        }

        account_name = account_map.get(self.body_type, "Rental Fleet - Sedans")
        account = get_account(account_name, company, "Fixed Asset")

        return account or self.get_default_fixed_asset_account(company)

    def get_default_fixed_asset_account(self, company):
        """Get default fixed asset account"""
        return frappe.db.get_value(
            "Account",
            {"account_type": "Fixed Asset", "company": company, "is_group": 0},
            "name"
        )


def validate_vehicle(doc, method):
    """Hook for validate."""
    pass


def on_vehicle_update(doc, method):
    """Hook for on_update."""
    # Update related documents if status changed
    if doc.has_value_changed("status"):
        frappe.publish_realtime(
            "vehicle_status_changed",
            {"vehicle": doc.name, "status": doc.status},
        )
