# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate
from frappe import _

class MaintenanceJob(Document):
    def validate(self):
        self.calculate_actual_hours()

    def calculate_actual_hours(self):
        """Calculate actual hours from start and close datetime"""
        if self.start_datetime and self.close_datetime:
            from datetime import datetime
            start = datetime.strptime(str(self.start_datetime), "%Y-%m-%d %H:%M:%S")
            close = datetime.strptime(str(self.close_datetime), "%Y-%m-%d %H:%M:%S")
            delta = close - start
            self.actual_hours = delta.total_seconds() / 3600

    def on_submit(self):
        """Create Purchase Invoice on job completion"""
        if self.status == "Completed" and self.actual_cost:
            self.create_purchase_invoice()

    @frappe.whitelist()
    def create_purchase_invoice(self):
        """Create Purchase Invoice for maintenance expense"""
        if not frappe.db.exists("DocType", "Purchase Invoice"):
            frappe.msgprint(_("ERPNext Purchase Invoice not available"))
            return

        if not self.actual_cost:
            frappe.throw(_("Actual cost is required to create invoice"))

        # Check if already created
        existing = frappe.db.get_value(
            "Purchase Invoice",
            {"maintenance_job": self.name, "docstatus": 1},
            "name"
        )

        if existing:
            frappe.msgprint(f"Purchase Invoice {existing} already exists")
            return existing

        # Create Purchase Invoice
        pi = frappe.new_doc("Purchase Invoice")

        # Get supplier (workshop/vendor)
        pi.supplier = self.vendor or "Maintenance Vendors"

        # Ensure supplier exists
        if not frappe.db.exists("Supplier", pi.supplier):
            self.create_supplier(pi.supplier)

        pi.posting_date = getdate(self.job_date)
        pi.due_date = getdate(self.job_date)

        # Get company
        pi.company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

        # Set custom fields
        pi.vehicle = self.vehicle
        pi.expense_type = "Maintenance"
        pi.maintenance_job = self.name
        pi.odometer_reading = flt(self.odometer_reading)

        # Add maintenance service item
        pi.append("items", {
            "item_code": self.get_or_create_maintenance_item(),
            "item_name": f"Maintenance - {self.service_type}",
            "description": f"Maintenance Job {self.name} for {self.vehicle}",
            "qty": 1,
            "rate": flt(self.actual_cost),
            "amount": flt(self.actual_cost),
            "expense_account": self.get_maintenance_account(pi.company),
        })

        # Add parts if any (assuming there's a parts child table)
        if hasattr(self, 'parts') and self.parts:
            for part in self.parts:
                pi.append("items", {
                    "item_code": self.get_or_create_parts_item(),
                    "item_name": part.part_name,
                    "description": part.description or part.part_name,
                    "qty": flt(part.quantity) if hasattr(part, 'quantity') else 1,
                    "rate": flt(part.unit_cost) if hasattr(part, 'unit_cost') else 0,
                    "amount": flt(part.total_cost) if hasattr(part, 'total_cost') else 0,
                    "expense_account": self.get_maintenance_account(pi.company),
                })

        # Save and submit
        pi.flags.ignore_mandatory = True
        pi.flags.ignore_validate = True
        pi.save(ignore_permissions=True)
        pi.submit()

        frappe.msgprint(f"Purchase Invoice {pi.name} created", indicator="green")
        return pi.name

    def create_supplier(self, supplier_name):
        """Create supplier if doesn't exist"""
        if not frappe.db.exists("Supplier", supplier_name):
            supplier = frappe.new_doc("Supplier")
            supplier.supplier_name = supplier_name
            supplier.supplier_group = "All Supplier Groups"
            supplier.supplier_type = "Company"
            supplier.insert(ignore_permissions=True)

    def get_or_create_maintenance_item(self):
        """Get or create maintenance service item"""
        item_code = "Maintenance Service"

        if not frappe.db.exists("Item", item_code):
            item = frappe.new_doc("Item")
            item.item_code = item_code
            item.item_name = "Maintenance Service"
            item.item_group = "Services"
            item.stock_uom = "Nos"
            item.is_stock_item = 0
            item.insert(ignore_permissions=True)

        return item_code

    def get_or_create_parts_item(self):
        """Get or create maintenance parts item"""
        item_code = "Maintenance Parts"

        if not frappe.db.exists("Item", item_code):
            item = frappe.new_doc("Item")
            item.item_code = item_code
            item.item_name = "Maintenance Parts"
            item.item_group = "Products"
            item.stock_uom = "Nos"
            item.is_stock_item = 0
            item.insert(ignore_permissions=True)

        return item_code

    def get_maintenance_account(self, company):
        """Get maintenance expense account"""
        from right_hire.setup.accounts import get_account
        return get_account("Vehicle Maintenance", company, "Expense Account")
