import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class Customer(Document):
    def validate(self):
        self.validate_kyc()
        self.validate_license()
        self.update_totals()
        
    def validate_kyc(self):
        """Validate KYC documents"""
        if self.customer_type == "Individual":
            if self.id_expiry and getdate(self.id_expiry) < getdate(nowdate()):
                frappe.msgprint("ID has expired", alert=True)
            if self.passport_expiry and getdate(self.passport_expiry) < getdate(nowdate()):
                frappe.msgprint("Passport has expired", alert=True)
    
    def validate_license(self):
        """Validate driving license"""
        if self.customer_type == "Individual" and self.license_expiry:
            if getdate(self.license_expiry) < getdate(nowdate()):
                frappe.throw("Driving license has expired")
    
    def update_totals(self):
        """Update financial totals"""
        # Total outstanding from invoices
        self.total_outstanding = frappe.db.get_value("Invoice",
            {"customer": self.name, "status": ["!=", "Paid"]},
            "sum(outstanding)") or 0
        
        # Total bookings
        self.total_bookings = frappe.db.count("Rental Agreement",
            {"customer": self.name})
        
        # Lifetime value
        self.lifetime_value = frappe.db.get_value("Rental Agreement",
            {"customer": self.name},
            "sum(grand_total)") or 0
    
    def after_insert(self):
        """Sync with ERPNext if enabled"""
        if self.sync_with_erpnext and frappe.db.exists("DocType", "Customer"):
            self.create_erpnext_customer()
    
    def create_erpnext_customer(self):
        """Create corresponding ERPNext customer"""
        try:
            if not self.erpnext_customer:
                customer = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": self.customer_name,
                    "customer_type": self.customer_type,
                    "customer_group": "Commercial" if self.customer_type == "Company" else "Individual",
                    "territory": "All Territories",
                    "mobile_no": self.mobile,
                    "email_id": self.email
                })
                customer.insert(ignore_permissions=True)
                self.db_set("erpnext_customer", customer.name)
        except Exception as e:
            frappe.log_error(f"Failed to create ERPNext customer: {str(e)}")