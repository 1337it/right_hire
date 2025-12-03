# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def after_install():
    """Setup after installation"""
    create_custom_roles()
    create_default_branches()
    create_default_rate_plans()
    frappe.db.commit()

def create_custom_roles():
    """Create custom roles for Right Hire"""
    roles = [
        {"role_name": "Right Hire Admin", "desk_access": 1},
        {"role_name": "Fleet Manager", "desk_access": 1},
        {"role_name": "Counter Agent", "desk_access": 1},
        {"role_name": "Fleet Ops", "desk_access": 1},
        {"role_name": "Mechanic", "desk_access": 1}
    ]
    
    for role in roles:
        if not frappe.db.exists("Role", role["role_name"]):
            doc = frappe.get_doc({
                "doctype": "Role",
                "role_name": role["role_name"],
                "desk_access": role["desk_access"]
            })
            doc.insert(ignore_permissions=True)
            frappe.logger().info(f"Created role: {role['role_name']}")

def create_default_branches():
    """Create a default branch"""
    if not frappe.db.exists("Branch", "Main Branch"):
        branch = frappe.get_doc({
            "doctype": "Branch",
            "branch_name": "Main Branch",
            "address": "Head Office"
        })
        branch.insert(ignore_permissions=True)
        frappe.logger().info("Created default branch: Main Branch")

def create_default_rate_plans():
    """Create default rate plans"""
    rate_plans = [
        {
            "rate_plan_name": "Standard Daily",
            "rate_type": "Daily",
            "base_rate": 150.00,
            "free_km": 200,
            "overage_per_km": 0.50,
            "deposit": 500.00
        },
        {
            "rate_plan_name": "Standard Weekly",
            "rate_type": "Weekly",
            "base_rate": 900.00,
            "free_km": 1400,
            "overage_per_km": 0.45,
            "deposit": 1000.00
        },
        {
            "rate_plan_name": "Standard Monthly",
            "rate_type": "Monthly",
            "base_rate": 3000.00,
            "free_km": 6000,
            "overage_per_km": 0.40,
            "deposit": 2000.00
        }
    ]
    
    for plan in rate_plans:
        if not frappe.db.exists("Rate Plan", plan["rate_plan_name"]):
            doc = frappe.get_doc({"doctype": "Rate Plan", **plan})
            doc.insert(ignore_permissions=True)
            frappe.logger().info(f"Created rate plan: {plan['rate_plan_name']}")
