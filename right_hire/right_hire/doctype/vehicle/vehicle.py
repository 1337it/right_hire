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
        """Update custom_plate_art when custom_plate_code or plate_no changes."""
        if self.has_value_changed("custom_plate_code") or self.has_value_changed("plate_no"):
            # Build plate art from plate_no and custom_plate_code
            plate_code = self.custom_plate_code or ""
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

    def update_status(self, new_status, reason=None, reference_doctype=None, reference_name=None):
        """Update vehicle status and log the change."""
        old_status = self.status
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
