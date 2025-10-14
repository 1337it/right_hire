import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, flt, add_days

class MaintenanceJob(Document):
    def validate(self):
        self.calculate_hours()
        self.calculate_costs()
        
    def on_update(self):
        if self.has_value_changed("job_status"):
            self.handle_status_change()
    
    def calculate_hours(self):
        """Calculate actual hours and downtime"""
        if self.start_datetime and self.close_datetime:
            hours = (get_datetime(self.close_datetime) - get_datetime(self.start_datetime)).total_seconds() / 3600
            self.actual_hours = hours
            
        if self.open_datetime and self.close_datetime:
            downtime = (get_datetime(self.close_datetime) - get_datetime(self.open_datetime)).total_seconds() / 3600
            self.downtime_hours = downtime
    
    def calculate_costs(self):
        """Calculate total costs from parts and tasks"""
        parts_cost = sum([flt(part.cost) for part in self.parts])
        tasks_cost = sum([flt(task.cost) for task in self.tasks])
        self.actual_cost = parts_cost + tasks_cost
    
    def handle_status_change(self):
        """Handle vehicle status changes based on job status"""
        vehicle = frappe.get_doc("Vehicle", self.vehicle)
        
        if self.job_status == "In Progress":
            vehicle.update_status("Under Maintenance", 
                                reason=f"Maintenance Job {self.name}")
            if not self.start_datetime:
                self.start_datetime = frappe.utils.now()
                
        elif self.job_status == "Completed":
            vehicle.update_status("Available", 
                                reason=f"Maintenance Job {self.name} completed")
            if not self.close_datetime:
                self.close_datetime = frappe.utils.now()
            
            # Update vehicle service history
            self.update_vehicle_service_history()
            
            # Calculate next service
            self.calculate_next_service()
    
    def update_vehicle_service_history(self):
        """Add entry to vehicle service history"""
        vehicle = frappe.get_doc("Vehicle", self.vehicle)
        vehicle.append("service_history", {
            "service_date": self.job_date,
            "service_type": self.service_type,
            "description": self.description,
            "vendor": self.workshop_name,
            "cost": self.actual_cost,
            "odometer_reading": self.odometer_reading
        })
        vehicle.last_service_date = self.job_date
        vehicle.save(ignore_permissions=True)
    
    def calculate_next_service(self):
        """Calculate next service due"""
        if self.service_interval_km and self.odometer_reading:
            self.next_service_km = self.odometer_reading + self.service_interval_km
            
            # Update vehicle
            vehicle = frappe.get_doc("Vehicle", self.vehicle)
            vehicle.next_service_due = self.next_service_date
            vehicle.save(ignore_permissions=True)
    
    @frappe.whitelist()
    def start_job(self):
        """Start the maintenance job"""
        if self.job_status != "Scheduled":
            frappe.throw("Job must be scheduled to start")
        
        self.job_status = "In Progress"
        self.start_datetime = frappe.utils.now()
        self.save()
        frappe.msgprint("Job started")
    
    @frappe.whitelist()
    def complete_job(self):
        """Complete the maintenance job"""
        if self.job_status != "In Progress":
            frappe.throw("Job must be in progress to complete")
        
        if not self.actual_cost:
            frappe.msgprint("Please enter actual cost", alert=True)
        
        self.job_status = "Completed"
        self.close_datetime = frappe.utils.now()
        self.save()
        frappe.msgprint("Job completed successfully")