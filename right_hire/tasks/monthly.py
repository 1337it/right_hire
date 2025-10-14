# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate, add_months, get_first_day, get_last_day, today

def generate_lease_invoices():
    """Generate monthly invoices for active lease contracts"""
    current_date = getdate(today())
    
    # Get active lease contracts
    leases = frappe.get_all(
        "Lease Contract",
        filters={
            "lease_status": "Active",
            "billing_cycle": "Monthly"
        },
        fields=["name", "billing_day"]
    )
    
    for lease in leases:
        try:
            lease_doc = frappe.get_doc("Lease Contract", lease.name)
            
            # Check if invoice is due
            if current_date.day == lease.billing_day:
                # Find pending schedule line
                for schedule in lease_doc.invoice_schedule:
                    if schedule.status == "Pending" and getdate(schedule.period_start) <= current_date:
                        invoice_name = lease_doc.create_monthly_invoice(
                            schedule.period_start,
                            schedule.period_end
                        )
                        frappe.logger().info(f"Created invoice {invoice_name} for lease {lease.name}")
                        break
        except Exception as e:
            frappe.log_error(f"Failed to create invoice for lease {lease.name}: {str(e)}")

def calculate_profitability():
    """Calculate monthly profitability per vehicle"""
    current_date = today()
    start_date = get_first_day(current_date)
    end_date = get_last_day(current_date)
    
    vehicles = frappe.get_all("Vehicle", 
                             filters={"status": ["!=", "Deactivated"]},
                             pluck="name")
    
    for vehicle in vehicles:
        try:
            # Get revenue
            revenue = frappe.db.sql("""
                SELECT SUM(grand_total) as total
                FROM tabRental Agreement
                WHERE vehicle = %s
                AND DATE(start_datetime) >= %s
                AND DATE(start_datetime) <= %s
                AND agreement_status NOT IN ('Cancelled', 'Draft')
            """, (vehicle, start_date, end_date), as_dict=True)
            
            # Get maintenance costs
            maintenance_cost = frappe.db.sql("""
                SELECT SUM(actual_cost) as total
                FROM tabMaintenance Job
                WHERE vehicle = %s
                AND DATE(job_date) >= %s
                AND DATE(job_date) <= %s
                AND job_status = 'Completed'
            """, (vehicle, start_date, end_date), as_dict=True)
            
            total_revenue = revenue[0].total if revenue and revenue[0].total else 0
            total_cost = maintenance_cost[0].total if maintenance_cost and maintenance_cost[0].total else 0
            net_profit = total_revenue - total_cost
            
            # Update vehicle
            vehicle_doc = frappe.get_doc("Vehicle", vehicle)
            vehicle_doc.total_revenue = total_revenue
            vehicle_doc.total_maintenance_cost = total_cost
            vehicle_doc.net_profit = net_profit
            vehicle_doc.save(ignore_permissions=True)
            
            frappe.logger().info(f"Updated profitability for vehicle {vehicle}")
        except Exception as e:
            frappe.log_error(f"Failed to calculate profitability for {vehicle}: {str(e)}")
