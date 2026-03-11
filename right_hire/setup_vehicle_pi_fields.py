"""
Create custom fields to link Vehicle and Purchase Invoice
Run with: bench --site app.righthire.ae execute right_hire.setup_vehicle_pi_fields.create_custom_fields
"""

import frappe

def create_custom_fields():
    """Create custom fields to link Vehicle and Purchase Invoice"""
    frappe.set_user("Administrator")

    print("\nCreating custom fields for Vehicle-Purchase Invoice linking...")
    print("="*60)

    # Custom field on Vehicle to link to Purchase Invoice
    if not frappe.db.exists("Custom Field", "Vehicle-purchase_invoice"):
        try:
            cf = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Vehicle",
                "fieldname": "purchase_invoice",
                "label": "Purchase Invoice",
                "fieldtype": "Link",
                "options": "Purchase Invoice",
                "insert_after": "supplier",
                "read_only": 0,
            })
            cf.insert(ignore_permissions=True)
            print("✓ Created custom field: Vehicle.purchase_invoice")
        except Exception as e:
            print(f"✗ Error creating Vehicle.purchase_invoice: {str(e)}")
    else:
        print("✓ Custom field Vehicle.purchase_invoice already exists")

    # Custom field on Purchase Invoice Item to link to Vehicle
    if not frappe.db.exists("Custom Field", "Purchase Invoice Item-vehicle"):
        try:
            cf = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Purchase Invoice Item",
                "fieldname": "vehicle",
                "label": "Vehicle",
                "fieldtype": "Link",
                "options": "Vehicle",
                "insert_after": "item_code",
                "read_only": 0,
            })
            cf.insert(ignore_permissions=True)
            print("✓ Created custom field: Purchase Invoice Item.vehicle")
        except Exception as e:
            print(f"✗ Error creating Purchase Invoice Item.vehicle: {str(e)}")
    else:
        print("✓ Custom field Purchase Invoice Item.vehicle already exists")

    frappe.db.commit()

    print("\n" + "="*60)
    print("✓ Custom fields setup completed!")
    print("="*60 + "\n")

    return {"success": True, "message": "Custom fields created"}
