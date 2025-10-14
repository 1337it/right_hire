# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_days, nowdate, date_diff, today

def calculate_daily_utilization():
    """Calculate daily utilization for all vehicles"""
    vehicles = frappe.get_all("Vehicle", 
                             filters={"status": ["!=", "Deactivated"]}, 
                             pluck="name")
    
    for vehicle_name in vehicles:
        try:
            calculate_vehicle_utilization(vehicle_name, getdate())
        except Exception as e:
            frappe.log_error(f"Failed to calculate utilization for {vehicle_name}: {str(e)}")

def calculate_vehicle_utilization(vehicle, date):
    """Calculate utilization for a specific vehicle and date"""
    # Get agreements for this vehicle on this date
    agreements = frappe.db.sql("""
        SELECT name, start_datetime, end_datetime, grand_total
        FROM tabRental Agreement
        WHERE vehicle = %s
        AND DATE(start_datetime) <= %s
        AND DATE(end_datetime) >= %s
        AND agreement_status NOT IN ('Cancelled', 'Draft')
    """, (vehicle, date, date), as_dict=True)
    
    # Get maintenance jobs
    maintenance = frappe.db.sql("""
        SELECT actual_hours
        FROM tabMaintenance Job
        WHERE vehicle = %s
        AND DATE(job_date) = %s
        AND job_status = 'Completed'
    """, (vehicle, date), as_dict=True)
    
    rented_hours = 0
    revenue = 0
    
    for agreement in agreements:
        # Calculate hours for this day
        hours = 24  # Simplified - assume full day if active
        rented_hours += hours
        
        # Prorate revenue
        total_days = date_diff(agreement.end_datetime, agreement.start_datetime) or 1
        daily_revenue = agreement.grand_total / total_days
        revenue += daily_revenue
    
    maintenance_hours = sum([m.actual_hours or 0 for m in maintenance])
    idle_hours = 24 - rented_hours - maintenance_hours
    
    utilization_pct = (rented_hours / 24) * 100 if rented_hours else 0
    
    # Create or update snapshot
    snapshot_name = f"{vehicle}-{date}"
    if frappe.db.exists("Utilization Snapshot", snapshot_name):
        snapshot = frappe.get_doc("Utilization Snapshot", snapshot_name)
    else:
        snapshot = frappe.new_doc("Utilization Snapshot")
        snapshot.vehicle = vehicle
        snapshot.snapshot_date = date
    
    snapshot.total_hours = 24
    snapshot.rented_hours = rented_hours
    snapshot.idle_hours = idle_hours
    snapshot.maintenance_hours = maintenance_hours
    snapshot.utilization_pct = utilization_pct
    snapshot.revenue = revenue
    snapshot.rental_days = rented_hours / 24
    
    snapshot.save(ignore_permissions=True)

def send_expiry_alerts():
    """Send alerts for expiring documents"""
    # Insurance expiring in 30 days
    expiring_insurance = frappe.get_all(
        "Insurance Policy",
        filters={
            "end_date": ["between", [today(), add_days(today(), 30)]],
            "is_active": 1
        },
        fields=["name", "policy_number", "end_date"]
    )
    
    for policy in expiring_insurance:
        send_alert("Insurance Policy Expiring", 
                   f"Policy {policy.policy_number} expires on {policy.end_date}")
    
    # Vehicle registration expiring in 30 days
    expiring_registration = frappe.get_all(
        "Vehicle",
        filters={
            "registration_expiry": ["between", [today(), add_days(today(), 30)]],
            "status": ["!=", "Deactivated"]
        },
        fields=["name", "plate_no", "registration_expiry"]
    )
    
    for vehicle in expiring_registration:
        send_alert("Vehicle Registration Expiring",
                   f"Vehicle {vehicle.plate_no} registration expires on {vehicle.registration_expiry}")
    
    # Customer licenses expiring in 30 days
    expiring_licenses = frappe.get_all(
        "Customer",
        filters={
            "license_expiry": ["between", [today(), add_days(today(), 30)]],
            "customer_type": "Individual"
        },
        fields=["name", "customer_name", "license_expiry"]
    )
    
    for customer in expiring_licenses:
        send_alert("Customer License Expiring",
                   f"Customer {customer.customer_name} license expires on {customer.license_expiry}")

def check_maintenance_due():
    """Check vehicles due for maintenance"""
    vehicles = frappe.get_all(
        "Vehicle",
        filters={
            "status": ["!=", "Deactivated"],
            "next_service_due": ["<=", add_days(today(), 7)]
        },
        fields=["name", "plate_no", "next_service_due", "odometer"]
    )
    
    for vehicle in vehicles:
        send_alert("Maintenance Due",
                   f"Vehicle {vehicle.plate_no} is due for maintenance on {vehicle.next_service_due}")

def send_alert(subject, message):
    """Send alert to admin users"""
    admins = frappe.get_all("Has Role", 
                           filters={"role": "Right Hire Admin", "parenttype": "User"}, 
                           pluck="parent")
    
    for admin in admins:
        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": subject,
                "email_content": message,
                "for_user": admin,
                "type": "Alert"
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Failed to send alert to {admin}: {str(e)}")
