# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

def generate_utilization_report():
    """Generate weekly utilization summary report"""
    end_date = today()
    start_date = add_days(end_date, -7)
    
    vehicles = frappe.get_all("Vehicle", 
                             filters={"status": ["!=", "Deactivated"]},
                             pluck="name")
    
    report_data = []
    
    for vehicle in vehicles:
        snapshots = frappe.get_all(
            "Utilization Snapshot",
            filters={
                "vehicle": vehicle,
                "snapshot_date": ["between", [start_date, end_date]]
            },
            fields=["utilization_pct", "revenue", "rented_hours"]
        )
        
        if snapshots:
            avg_utilization = sum([s.utilization_pct for s in snapshots]) / len(snapshots)
            total_revenue = sum([s.revenue for s in snapshots])
            total_hours = sum([s.rented_hours for s in snapshots])
            
            report_data.append({
                "vehicle": vehicle,
                "avg_utilization": avg_utilization,
                "total_revenue": total_revenue,
                "total_hours": total_hours
            })
    
    report_data.sort(key=lambda x: x["avg_utilization"], reverse=True)
    send_weekly_report(report_data, start_date, end_date)

def send_weekly_report(data, start_date, end_date):
    """Send weekly report to fleet managers"""
    managers = frappe.get_all("Has Role",
                             filters={"role": ["in", ["Fleet Manager", "Right Hire Admin"]], 
                                     "parenttype": "User"},
                             pluck="parent")
    
    if not managers or not data:
        return
    
    # Build simple text report
    message_lines = []
    message_lines.append("Weekly Fleet Utilization Report")
    message_lines.append("=" * 50)
    message_lines.append("Period: {0} to {1}".format(start_date, end_date))
    message_lines.append("")
    message_lines.append("{:<20} {:>15} {:>15} {:>15}".format(
        "Vehicle", "Utilization %", "Revenue", "Hours"
    ))
    message_lines.append("-" * 70)
    
    for row in data:
        message_lines.append("{:<20} {:>14.2f}% {:>14.2f} {:>14.2f}".format(
            row['vehicle'][:20],
            row['avg_utilization'],
            row['total_revenue'],
            row['total_hours']
        ))
    
    message_lines.append("-" * 70)
    message_lines.append("")
    message_lines.append("Total Vehicles: {0}".format(len(data)))
    
    message_text = "\n".join(message_lines)
    
    for manager in managers:
        try:
            frappe.sendmail(
                recipients=[manager],
                subject="Weekly Fleet Utilization Report - {0} to {1}".format(start_date, end_date),
                message="<pre>{0}</pre>".format(message_text)
            )
        except Exception as e:
            frappe.log_error("Failed to send weekly report to {0}: {1}".format(manager, str(e)))
