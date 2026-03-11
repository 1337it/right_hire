# Copyright (c) 2024, Right Hire and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def after_install():
    """Setup after installation"""
    create_custom_roles()
    create_default_branches()
    create_default_rate_plans()
    setup_erpnext_accounts()
    create_custom_fields()
    setup_workspace_api_status()
    frappe.db.commit()


def after_migrate():
    """Run after migrate to setup workspace widgets"""
    setup_workspace_api_status()
    frappe.db.commit()

def setup_erpnext_accounts():
    """Setup ERPNext accounts if ERPNext is installed"""
    if not frappe.db.exists("DocType", "Account"):
        frappe.logger().info("ERPNext not installed, skipping account setup")
        return

    # Get default company
    company = frappe.db.get_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        frappe.logger().warn("No default company found, skipping account setup")
        return

    frappe.logger().info(f"Setting up ERPNext accounts for company: {company}")

    try:
        from right_hire.setup.accounts import create_rental_accounts, setup_default_accounts, setup_cost_centers
        create_rental_accounts(company)
        setup_default_accounts(company)
        setup_cost_centers(company)
        frappe.logger().info("ERPNext accounts setup completed")
    except Exception as e:
        frappe.log_error(f"Failed to setup ERPNext accounts: {str(e)}", "ERPNext Account Setup")

def create_custom_fields():
    """Create custom fields for ERPNext integration"""
    if not frappe.db.exists("DocType", "Sales Invoice"):
        frappe.logger().info("ERPNext not installed, skipping custom fields")
        return

    try:
        from right_hire.setup.custom_fields import create_accounting_custom_fields
        create_accounting_custom_fields()
        frappe.logger().info("Custom fields created successfully")
    except Exception as e:
        frappe.log_error(f"Failed to create custom fields: {str(e)}", "Custom Fields Creation")

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


def setup_workspace_api_status():
    """Add API Status Dashboard widget to the Right Hire workspace"""
    import json

    # First ensure the Custom HTML Block exists
    if not frappe.db.exists("Custom HTML Block", "API Status Dashboard"):
        frappe.logger().info("Creating API Status Dashboard custom block")
        block = frappe.get_doc({
            "doctype": "Custom HTML Block",
            "name": "API Status Dashboard",
            "private": 0,
            "html": '<div id="api-status-container"><div class="api-loading"><div class="spinner-border text-primary" role="status"></div><span>Loading API Status...</span></div></div>',
            "script": """// Load API status when block is rendered
frappe.call({
  method: 'right_hire.right_hire.api_status_dashboard.get_api_status_html',
  callback: function(r) {
    if (r.message) {
      root_element.querySelector('#api-status-container').innerHTML = r.message;
    } else {
      root_element.querySelector('#api-status-container').innerHTML = '<div class="api-status-widget" style="padding: 15px; background: #f8f9fa; border-radius: 8px;"><p style="color: #6c757d; margin: 0;">Unable to load API status. Please refresh the page.</p></div>';
    }
  }
});

// Auto-refresh every 60 seconds
setInterval(function() {
  frappe.call({
    method: 'right_hire.right_hire.api_status_dashboard.get_api_status_html',
    callback: function(r) {
      if (r.message) {
        root_element.querySelector('#api-status-container').innerHTML = r.message;
      }
    }
  });
}, 60000);""",
            "style": """.api-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  color: #6c757d;
}

.api-loading .spinner-border {
  width: 20px;
  height: 20px;
}"""
        })
        block.insert(ignore_permissions=True)
        frappe.logger().info("Created API Status Dashboard custom block")

    # Now update the Dashboard workspace
    workspace = frappe.db.get_value("Workspace", {"name": "Dashboard", "module": "Right Hire"}, "name")
    if not workspace:
        frappe.logger().info("Right Hire Dashboard workspace not found")
        return

    ws_doc = frappe.get_doc("Workspace", workspace)

    # Parse existing content
    try:
        content = json.loads(ws_doc.content) if ws_doc.content else []
    except (json.JSONDecodeError, TypeError):
        content = []

    # Check if API Status section already exists
    api_status_exists = any(
        item.get("id") == "api_status_section" or
        (item.get("type") == "custom_block" and item.get("data", {}).get("custom_block_name") == "API Status Dashboard")
        for item in content
    )

    if api_status_exists:
        frappe.logger().info("API Status widget already exists in Dashboard workspace")
        return

    # Add API Status section at the beginning
    api_status_content = [
        {
            "id": "api_status_section",
            "type": "header",
            "data": {"text": '<span class="h4">API Integration Status</span>', "col": 12}
        },
        {
            "id": "api_status_widget",
            "type": "custom_block",
            "data": {"custom_block_name": "API Status Dashboard", "col": 12}
        },
        {
            "id": "api_status_spacer",
            "type": "spacer",
            "data": {"col": 12}
        }
    ]

    # Insert at the beginning of content
    content = api_status_content + content

    ws_doc.content = json.dumps(content)
    ws_doc.save(ignore_permissions=True)
    frappe.logger().info("Added API Status widget to Dashboard workspace")
