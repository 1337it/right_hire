import frappe
import string
import random
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class Customer(Document):
    def before_insert(self):
        if not self.account_id:
            self.account_id = self.generate_account_id()

    @staticmethod
    def generate_account_id():
        chars = string.ascii_uppercase + string.digits
        for _ in range(20):
            code = "RH-" + "".join(random.choices(chars, k=6))
            if not frappe.db.exists("Customer", {"account_id": code}):
                return code
        frappe.throw("Could not generate a unique account ID. Please try again.")

    def validate(self):
        self.validate_kyc()
        self.validate_license()
        self.validate_company_documents()
        self.update_company_documents_status()
        self.update_totals()
        self.update_portal_user_info()
        
    def validate_kyc(self):
        """Validate KYC documents"""
        today = getdate(nowdate())

        # Validate Emirates ID / National ID expiry
        if self.id_expiry and getdate(self.id_expiry) < today:
            frappe.msgprint("Emirates ID / National ID has expired", alert=True)

        # Validate Passport expiry
        if self.passport_expiry and getdate(self.passport_expiry) < today:
            frappe.msgprint("Passport has expired", alert=True)

    def validate_license(self):
        """Validate driving license"""
        if self.license_expiry:
            if getdate(self.license_expiry) < getdate(nowdate()):
                frappe.msgprint("Driving license has expired", alert=True)

    def validate_company_documents(self):
        """Validate company documents (TRN, Trade License, Credit Application)"""
        if self.customer_type != "Company":
            return

        today = getdate(nowdate())

        # Validate TRN number format (15 digits for UAE)
        if self.trn_number and not self.trn_number.replace(" ", "").isdigit():
            frappe.throw("TRN number must contain only digits")

        if self.trn_number and len(self.trn_number.replace(" ", "")) != 15:
            frappe.msgprint("TRN number should be 15 digits for UAE", alert=True)

        # Check document expiry
        if self.credit_application_expiry and getdate(self.credit_application_expiry) < today:
            frappe.msgprint("Credit Application has expired", alert=True)

        if self.trn_certificate_expiry and getdate(self.trn_certificate_expiry) < today:
            frappe.msgprint("TRN Certificate has expired", alert=True)

        if self.trade_license_expiry and getdate(self.trade_license_expiry) < today:
            frappe.msgprint("Trade License has expired", alert=True)

    def update_company_documents_status(self):
        """Calculate and update overall company documents status"""
        if self.customer_type != "Company":
            self.company_documents_status = "Not Applicable"
            return

        from frappe.utils import add_days

        today = getdate(nowdate())
        thirty_days_ahead = add_days(today, 30)

        docs = [
            {
                'file': self.credit_application_file,
                'number': self.credit_application_number,
                'expiry': self.credit_application_expiry,
                'name': 'Credit Application'
            },
            {
                'file': self.trn_certificate_file,
                'number': self.trn_number,
                'expiry': self.trn_certificate_expiry,
                'name': 'TRN Certificate'
            },
            {
                'file': self.trade_license_file,
                'number': self.trade_license_number,
                'expiry': self.trade_license_expiry,
                'name': 'Trade License'
            }
        ]

        has_expired = False
        has_expiring_soon = False
        has_missing = False

        for doc in docs:
            # Check if document is missing (no file or no scanned number)
            if not doc['file'] or not doc['number']:
                has_missing = True
                continue

            # Check expiry status
            if doc['expiry']:
                expiry_date = getdate(doc['expiry'])
                if expiry_date < today:
                    has_expired = True
                elif expiry_date <= thirty_days_ahead:
                    has_expiring_soon = True

        # Determine overall status (priority: Expired > Missing > Expiring Soon > All Valid)
        if has_expired:
            self.company_documents_status = "Expired"
        elif has_missing:
            self.company_documents_status = "Missing Documents"
        elif has_expiring_soon:
            self.company_documents_status = "Expiring Soon"
        else:
            self.company_documents_status = "All Valid"
    
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
        """Sync with ERPNext if enabled and create portal user"""
        if self.sync_with_erpnext and frappe.db.exists("DocType", "Customer"):
            self.create_erpnext_customer()
        if self.email:
            self.create_portal_user()
    
    def update_portal_user_info(self):
        """Keep portal_user and portal_user_enabled in sync with the actual User record."""
        if self.email and frappe.db.exists("User", self.email):
            self.portal_user = self.email
            self.portal_user_enabled = frappe.db.get_value("User", self.email, "enabled")
        else:
            self.portal_user = None
            self.portal_user_enabled = 0

    def create_portal_user(self):
        """Create a Website User so the customer can log into the portal"""
        if not self.email or frappe.db.exists("User", self.email):
            return
        try:
            user = frappe.get_doc({
                "doctype": "User",
                "email": self.email,
                "first_name": self.customer_name,
                "user_type": "Website User",
                "send_welcome_email": 1,
            })
            user.append("roles", {"role": "Customer"})
            user.insert(ignore_permissions=True)
            self.db_set("portal_user", self.email)
            self.db_set("portal_user_enabled", 1)
        except Exception as e:
            frappe.log_error(f"Failed to create portal user for {self.name}: {str(e)}")

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


@frappe.whitelist()
def set_portal_password(customer, new_password):
    """Set a new password for the customer's portal user."""
    doc = frappe.get_doc("Customer", customer)
    if not doc.portal_user:
        frappe.throw("No portal user linked to this customer")

    from frappe.utils.password import update_password
    update_password(doc.portal_user, new_password)
    frappe.msgprint(f"Password updated for {doc.portal_user}", alert=True)


@frappe.whitelist()
def create_portal_user_for_customer(customer):
    """Manually create a portal user for an existing customer."""
    doc = frappe.get_doc("Customer", customer)
    if not doc.email:
        frappe.throw("Customer has no email address. Please set an email first.")
    if frappe.db.exists("User", doc.email):
        doc.db_set("portal_user", doc.email)
        doc.db_set("portal_user_enabled", frappe.db.get_value("User", doc.email, "enabled"))
        frappe.msgprint(f"User {doc.email} already exists. Linked to customer.", alert=True)
        return
    doc.create_portal_user()
    frappe.msgprint(f"Portal user created for {doc.email}. Welcome email sent.", alert=True)
