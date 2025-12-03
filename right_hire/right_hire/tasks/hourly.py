# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, now_datetime, add_to_date

def check_reservation_conflicts():
    """Check for reservation conflicts hourly"""
    # Get reservations starting in next 24 hours
    next_24_hours = add_to_date(now_datetime(), hours=24)
    
    reservations = frappe.get_all(
        "Reservation",
        filters={
            "reservation_status": ["in", ["Confirmed", "Allocated"]],
            "pickup_datetime": ["<=", next_24_hours]
        },
        fields=["name", "vehicle", "pickup_datetime", "return_datetime"]
    )
    
    for reservation in reservations:
        if reservation.vehicle:
            # Check for conflicts
            conflicts = frappe.db.sql("""
                SELECT name FROM tabReservation
                WHERE vehicle = %s
                AND name != %s
                AND reservation_status IN ('Confirmed', 'Allocated')
                AND (
                    (pickup_datetime <= %s AND return_datetime >= %s)
                    OR (pickup_datetime <= %s AND return_datetime >= %s)
                    OR (pickup_datetime >= %s AND return_datetime <= %s)
                )
            """, (reservation.vehicle, reservation.name,
                  reservation.pickup_datetime, reservation.pickup_datetime,
                  reservation.return_datetime, reservation.return_datetime,
                  reservation.pickup_datetime, reservation.return_datetime))
            
            if conflicts:
                # Send alert
                frappe.publish_realtime("reservation_conflict", {
                    "reservation": reservation.name,
                    "conflicts": [c[0] for c in conflicts]
                })
                
                frappe.logger().warning(
                    f"Reservation conflict detected: {reservation.name} conflicts with {[c[0] for c in conflicts]}"
                )

def check_overdue_returns():
    """Check for overdue vehicle returns"""
    overdue_agreements = frappe.get_all(
        "Rental Agreement",
        filters={
            "agreement_status": "Active",
            "end_datetime": ["<", now()]
        },
        fields=["name", "customer", "vehicle", "end_datetime"]
    )
    
    for agreement in overdue_agreements:
        try:
            # Update status
            doc = frappe.get_doc("Rental Agreement", agreement.name)
            doc.agreement_status = "Due for Return"
            doc.is_overdue = 1
            doc.save(ignore_permissions=True)
            
            # Send notification
            send_overdue_notification(doc)
            
            frappe.logger().info(f"Marked agreement {agreement.name} as overdue")
        except Exception as e:
            frappe.log_error(f"Failed to process overdue agreement {agreement.name}: {str(e)}")

def send_overdue_notification(agreement):
    """Send overdue notification to customer and staff"""
    try:
        customer = frappe.get_doc("Customer", agreement.customer)
        
        if customer.email:
            frappe.sendmail(
                recipients=[customer.email],
                subject=f"Vehicle Return Overdue - {agreement.name}",
                message=f"""
                Dear {customer.customer_name},
                
                Your rental agreement {agreement.name} for vehicle {agreement.vehicle}
                was due for return on {agreement.end_datetime}.
                
                Please return the vehicle as soon as possible to avoid additional charges.
                
                Thank you,
                Right Hire Team
                """
            )
    except Exception as e:
        frappe.log_error(f"Failed to send overdue notification: {str(e)}")
