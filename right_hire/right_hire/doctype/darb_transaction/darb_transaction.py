# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class DarbTransaction(Document):
    def before_save(self):
        # Auto-link to active agreement if not already linked
        if self.vehicle and self.transaction_date and not self.linked_contract and not self.linked_agreement:
            self.auto_link_agreement()

        # Determine charge type
        self.determine_charge_type()

    def determine_charge_type(self):
        """Set charge_type based on whether vehicle was with customer at transaction time."""
        if not self.linked_contract and not self.linked_agreement:
            self.charge_type = "Non-Revenue"
            return

        if self.transaction_time:
            trans_datetime = get_datetime(f"{self.transaction_date} {self.transaction_time}")
        else:
            trans_datetime = get_datetime(self.transaction_date)

        agreement_type = "Lease Agreement" if self.linked_contract else "Rental Agreement"
        agreement_name = self.linked_contract or self.linked_agreement

        # Check movement records
        out_movement = frappe.db.sql("""
            SELECT name, out_date_time, in_date_time
            FROM `tabMovements`
            WHERE vehicle = %s AND agreement_type = %s AND agreement_no = %s
            AND out_date_time <= %s AND status IN ('Out Only', 'Completed', 'In Transit')
            ORDER BY out_date_time DESC LIMIT 1
        """, (self.vehicle, agreement_type, agreement_name, trans_datetime), as_dict=True)

        if not out_movement:
            self.charge_type = "Non-Revenue"
        elif out_movement[0].in_date_time and get_datetime(out_movement[0].in_date_time) <= trans_datetime:
            self.charge_type = "Non-Revenue"
        else:
            self.charge_type = "Revenue"

    def auto_link_agreement(self):
        """Auto-link to the active agreement at the time of transaction"""
        from right_hire.api.fines_tolls import get_active_agreement_for_vehicle_at_date

        agreement = get_active_agreement_for_vehicle_at_date(
            self.vehicle,
            self.transaction_date,
            self.transaction_time
        )

        if agreement:
            if agreement.get("agreement_type") == "Lease Agreement":
                self.linked_contract = agreement.get("agreement_name")
                self.lease_agreement = agreement.get("agreement_name")
            elif agreement.get("agreement_type") == "Rental Agreement":
                self.linked_agreement = agreement.get("agreement_name")
