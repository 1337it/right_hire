# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate, add_months, get_first_day, get_last_day, today

def generate_lease_invoices():
    """Generate monthly invoices for active lease contracts"""
    current_date = getdate(today())

    # Get active lease contracts for all billing cycles
    leases = frappe.get_all(
        "Lease Contract",
        filters={
            "lease_status": "Active",
            "docstatus": 1
        },
        fields=["name", "billing_day", "billing_cycle"]
    )

    for lease in leases:
        try:
            # Check if invoice is due based on billing cycle
            should_invoice = False

            if lease.billing_cycle == "Monthly":
                # Invoice on billing day
                if current_date.day == lease.billing_day:
                    should_invoice = True
            elif lease.billing_cycle == "Quarterly":
                # Invoice every 3 months on billing day
                if current_date.day == lease.billing_day and current_date.month in [1, 4, 7, 10]:
                    should_invoice = True
            elif lease.billing_cycle == "Annual":
                # Invoice once a year on billing day
                if current_date.day == lease.billing_day and current_date.month == 1:
                    should_invoice = True

            if should_invoice:
                lease_doc = frappe.get_doc("Lease Contract", lease.name)

                # Find next pending schedule line
                for schedule in lease_doc.invoice_schedule:
                    if schedule.status == "Pending" and getdate(schedule.period_start) <= current_date:
                        invoice_name = lease_doc.create_monthly_invoice(schedule)
                        frappe.logger().info(f"Created invoice {invoice_name} for lease {lease.name}")
                        frappe.db.commit()
                        break

        except Exception as e:
            frappe.log_error(f"Failed to create invoice for lease {lease.name}: {str(e)}", "Lease Invoice Generation")
            frappe.db.rollback()

def calculate_profitability():
    """Calculate monthly profitability per vehicle - includes lease revenue and purchase costs"""
    current_date = today()
    start_date = get_first_day(current_date)
    end_date = get_last_day(current_date)

    vehicles = frappe.get_all("Vehicle",
                             filters={"vehicle_status": ["!=", "Deactivated"]},
                             pluck="name")

    for vehicle in vehicles:
        try:
            # Revenue from Rental Agreements
            rental_revenue = frappe.db.sql("""
                SELECT SUM(grand_total) as total
                FROM `tabRental Agreement`
                WHERE vehicle = %s
                AND DATE(start_datetime) >= %s
                AND DATE(start_datetime) <= %s
                AND agreement_status NOT IN ('Cancelled', 'Draft')
            """, (vehicle, start_date, end_date), as_dict=True)

            # Revenue from Lease Contracts via Sales Invoices
            lease_revenue = 0
            if frappe.db.exists("DocType", "Sales Invoice"):
                lease_revenue_result = frappe.db.sql("""
                    SELECT SUM(grand_total) as total
                    FROM `tabSales Invoice`
                    WHERE vehicle = %s
                    AND lease_contract IS NOT NULL
                    AND posting_date >= %s
                    AND posting_date <= %s
                    AND docstatus = 1
                """, (vehicle, start_date, end_date), as_dict=True)
                lease_revenue = lease_revenue_result[0].total if lease_revenue_result and lease_revenue_result[0].total else 0

            # Costs from Purchase Invoices (maintenance, fuel, etc.)
            purchase_costs = 0
            if frappe.db.exists("DocType", "Purchase Invoice"):
                purchase_costs_result = frappe.db.sql("""
                    SELECT SUM(grand_total) as total
                    FROM `tabPurchase Invoice`
                    WHERE vehicle = %s
                    AND expense_type IN ('Maintenance', 'Fuel', 'Repairs', 'Insurance', 'Registration', 'Tires')
                    AND posting_date >= %s
                    AND posting_date <= %s
                    AND docstatus = 1
                """, (vehicle, start_date, end_date), as_dict=True)
                purchase_costs = purchase_costs_result[0].total if purchase_costs_result and purchase_costs_result[0].total else 0

            # Legacy maintenance costs (from Maintenance Job if not linked to Purchase Invoice)
            maintenance_cost = frappe.db.sql("""
                SELECT SUM(actual_cost) as total
                FROM `tabMaintenance Job`
                WHERE vehicle = %s
                AND DATE(job_date) >= %s
                AND DATE(job_date) <= %s
                AND status = 'Completed'
            """, (vehicle, start_date, end_date), as_dict=True)

            total_rental_revenue = rental_revenue[0].total if rental_revenue and rental_revenue[0].total else 0
            total_revenue = total_rental_revenue + lease_revenue

            total_purchase_costs = purchase_costs
            total_maintenance_cost = maintenance_cost[0].total if maintenance_cost and maintenance_cost[0].total else 0
            total_cost = total_purchase_costs + total_maintenance_cost

            net_profit = total_revenue - total_cost

            # Update vehicle
            vehicle_doc = frappe.get_doc("Vehicle", vehicle)
            vehicle_doc.total_revenue = total_revenue
            vehicle_doc.total_maintenance_cost = total_cost
            vehicle_doc.net_profit = net_profit
            vehicle_doc.save(ignore_permissions=True)

            frappe.logger().info(f"Updated profitability for vehicle {vehicle}: Revenue={total_revenue}, Cost={total_cost}, Profit={net_profit}")

        except Exception as e:
            frappe.log_error(f"Failed to calculate profitability for {vehicle}: {str(e)}", "Vehicle Profitability Calculation")
