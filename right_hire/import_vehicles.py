"""
Import Nissan Magnite vehicles from invoice 95074120
Run with: bench --site app.righthire.ae execute right_hire.import_vehicles.import_nissan_magnite_vehicles
"""

import frappe
from frappe import _

def import_nissan_magnite_vehicles():
    """Import 3 Nissan Magnite vehicles from invoice 95074120"""
    frappe.set_user("Administrator")

    print("="*60)
    print("Importing 3 Nissan Magnite vehicles from Invoice 95074120")
    print("="*60)

    # Step 1: Create supplier
    supplier = create_supplier()

    # Step 2: Create vehicle make
    make = create_vehicle_make()

    # Step 3: Create vehicle model
    model = create_vehicle_model(make)

    # Step 4: Create vehicles
    vehicles_data = [
        {
            'chassis_number': 'MDHBD0FA9SG023591',
            'engine_number': 'HRA0110618C',
        },
        {
            'chassis_number': 'MDHBD0FA0SG023608',
            'engine_number': 'HRA0110737C',
        },
        {
            'chassis_number': 'MDHBD0FA0SG023673',
            'engine_number': 'HRA0110730C',
        },
    ]

    vehicle_names = []
    for vehicle_data in vehicles_data:
        vehicle_name = create_vehicle(
            chassis=vehicle_data['chassis_number'],
            engine=vehicle_data['engine_number'],
            make=make,
            model=model,
            supplier=supplier
        )
        if vehicle_name:
            vehicle_names.append(vehicle_name)

    print(f"\n✓ Created {len(vehicle_names)} vehicles")

    # Step 5: Create Purchase Invoice
    if len(vehicle_names) == 3:
        pi_name = create_purchase_invoice(supplier, vehicle_names)
        if pi_name:
            print(f"\n{'='*60}")
            print("✓ IMPORT COMPLETED SUCCESSFULLY!")
            print(f"{'='*60}")
            print(f"\nCreated:")
            print(f"  - Supplier: {supplier}")
            print(f"  - Vehicle Make: {make}")
            print(f"  - Vehicle Model: {model}")
            print(f"  - Vehicles: {len(vehicle_names)}")
            for vn in vehicle_names:
                print(f"    • {vn}")
            print(f"  - Purchase Invoice: {pi_name}")
            print(f"\nTotal Investment: 148,050 AED (incl. VAT)")
            return {
                "success": True,
                "vehicles": vehicle_names,
                "purchase_invoice": pi_name
            }

    return {"success": False, "message": "Failed to create all vehicles"}


def create_supplier():
    """Create Al Masaood Automobiles supplier"""
    print("\n1. Creating supplier: Al Masaood Automobiles Co LLC...")

    supplier_name = "Al Masaood Automobiles Co LLC"

    # Check if supplier exists
    if frappe.db.exists("Supplier", supplier_name):
        print(f"   ✓ Supplier already exists: {supplier_name}")
        return supplier_name

    try:
        # Get or create supplier group
        supplier_group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
        if not supplier_group:
            # Create a default supplier group
            sg = frappe.get_doc({
                "doctype": "Supplier Group",
                "supplier_group_name": "All Supplier Groups",
                "is_group": 0,
            })
            sg.insert(ignore_permissions=True)
            supplier_group = sg.name
            frappe.db.commit()

        supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_group": supplier_group,
            "country": "United Arab Emirates",
            "tax_id": "100272094200003",
            "default_currency": "AED",
        })
        supplier.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✓ Created supplier: {supplier.name}")
        return supplier.name
    except Exception as e:
        print(f"   ✗ Error creating supplier: {str(e)}")
        frappe.db.rollback()
        raise


def create_vehicle_make():
    """Create/verify Nissan make"""
    print("\n2. Checking Vehicle Make: Nissan...")

    make = frappe.db.get_value("Vehicle Make", {"make_name": "Nissan"}, "name")

    if make:
        print(f"   ✓ Vehicle Make exists: {make}")
        return make

    try:
        make_doc = frappe.get_doc({
            "doctype": "Vehicle Make",
            "make_name": "Nissan",
        })
        make_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✓ Created Vehicle Make: {make_doc.name}")
        return make_doc.name
    except Exception as e:
        print(f"   ✗ Error creating make: {str(e)}")
        frappe.db.rollback()
        raise


def create_vehicle_model(make_name):
    """Create/verify Nissan Magnite model"""
    print("\n3. Checking Vehicle Model: Magnite...")

    model = frappe.db.get_value("Vehicle Model",
                                {"model_name": "Magnite", "make": make_name},
                                "name")

    if model:
        print(f"   ✓ Vehicle Model exists: {model}")
        return model

    try:
        model_doc = frappe.get_doc({
            "doctype": "Vehicle Model",
            "model_name": "Magnite",
            "make": make_name,
        })
        model_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✓ Created Vehicle Model: {model_doc.name}")
        return model_doc.name
    except Exception as e:
        print(f"   ✗ Error creating model: {str(e)}")
        frappe.db.rollback()
        raise


def create_vehicle(chassis, engine, make, model, supplier):
    """Create a vehicle record"""
    print(f"\n4. Creating vehicle with chassis: {chassis}...")

    # Check if vehicle exists
    if frappe.db.exists("Vehicle", {"chassis_number": chassis}):
        existing = frappe.db.get_value("Vehicle", {"chassis_number": chassis}, "name")
        print(f"   ✓ Vehicle already exists: {existing}")
        return existing

    try:
        # Generate vehicle ID from chassis (last 8 chars)
        vehicle_id = f"NIS-MAG-{chassis[-8:]}"
        # Use chassis as temp plate number until registered
        plate_no = chassis[-8:]

        # Get default branch
        branch = frappe.db.get_value("Branch", {}, "name") or "Main"

        vehicle = frappe.get_doc({
            "doctype": "Vehicle",
            "vehicle_id": vehicle_id,
            "plate_no": plate_no,
            "chassis_number": chassis,
            "engine_number": engine,
            "make": make,
            "model": model,
            "year": 2025,
            "variant": "2WD S CVT MID",
            "color": "White",
            "transmission": "CVT",
            "fuel_type": "Petrol",
            "body_type": "SUV",
            "branch": branch,
            "purchase_date": "2025-12-30",
            "purchase_cost": 49350.00,
            "supplier": supplier,
            "vehicle_status": "Available",
            "ownership": "Owned",
        })
        vehicle.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✓ Created vehicle: {vehicle.name} (ID: {vehicle_id})")
        return vehicle.name
    except Exception as e:
        print(f"   ✗ Error creating vehicle: {str(e)}")
        import traceback
        traceback.print_exc()
        frappe.db.rollback()
        return None


def create_purchase_invoice(supplier, vehicle_names):
    """Create Purchase Invoice for the three vehicles"""
    print("\n5. Creating Purchase Invoice...")

    try:
        # Check if invoice already exists
        existing = frappe.db.get_value("Purchase Invoice", {"bill_no": "95074120"}, "name")
        if existing:
            print(f"   ✓ Purchase Invoice already exists: {existing}")
            return existing

        # Get company
        company = frappe.defaults.get_defaults().get("company") or "Right Hire Car Rental L.L.C"

        # Create Purchase Invoice
        pi = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": supplier,
            "company": company,
            "posting_date": "2025-12-30",
            "bill_no": "95074120",
            "bill_date": "2025-12-30",
            "currency": "AED",
            "update_stock": 0,  # Don't update stock for non-stock items
        })

        # Get expense account for vehicles
        expense_account = frappe.db.get_value("Account",
                                             {"account_type": "Fixed Asset",
                                              "company": company,
                                              "is_group": 0},
                                             "name")

        if not expense_account:
            expense_account = frappe.db.get_value("Account",
                                                 {"company": company,
                                                  "is_group": 0},
                                                 "name", limit=1)

        print(f"   Using expense account: {expense_account}")

        # Get or create UOM
        uom = frappe.db.get_value("UOM", {}, "name")
        if not uom:
            # Create default UOM
            uom_doc = frappe.get_doc({
                "doctype": "UOM",
                "uom_name": "Unit",
            })
            uom_doc.insert(ignore_permissions=True)
            uom = uom_doc.name
            frappe.db.commit()

        # Get or create Item Group
        item_group = frappe.db.get_value("Item Group", {}, "name")
        if not item_group:
            # Create default item group
            ig = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": "All Item Groups",
                "is_group": 0,
            })
            ig.insert(ignore_permissions=True)
            item_group = ig.name
            frappe.db.commit()

        # Get or create Vehicle Item
        item_code = "VEHICLE-NISSAN-MAGNITE"
        if not frappe.db.exists("Item", item_code):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": "Nissan Magnite Vehicle",
                "item_group": item_group,
                "stock_uom": uom,
                "is_stock_item": 0,
                "is_fixed_asset": 0,  # Set to 0 to avoid Asset Category requirement
            })
            item.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"   ✓ Created Item: {item_code}")

        # Add items for each vehicle (3 vehicles @ 47,000 each = 141,000)
        for i, vehicle_name in enumerate(vehicle_names, 1):
            chassis = frappe.db.get_value("Vehicle", vehicle_name, "chassis_number")
            pi.append("items", {
                "item_code": item_code,
                "item_name": f"Nissan Magnite 2025 - {chassis}",
                "description": f"Nissan Magnite 2WD S CVT MID - Chassis: {chassis}",
                "qty": 1,
                "uom": uom,
                "rate": 47000.00,
                "expense_account": expense_account,
            })

        # Save the invoice
        pi.insert(ignore_permissions=True)
        print(f"   ✓ Created Purchase Invoice: {pi.name}")
        print(f"   • Net Total: {pi.net_total} AED")
        print(f"   • Grand Total: {pi.grand_total} AED")

        # Note: VAT needs to be configured in Tax templates
        # Submit the invoice
        pi.submit()
        frappe.db.commit()
        print(f"   ✓ Submitted Purchase Invoice: {pi.name}")

        return pi.name

    except Exception as e:
        print(f"   ✗ Error creating purchase invoice: {str(e)}")
        import traceback
        traceback.print_exc()
        frappe.db.rollback()
        return None
