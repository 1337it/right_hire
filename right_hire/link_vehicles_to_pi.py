"""
Link the 3 Nissan Magnite vehicles to their Purchase Invoice
Run with: bench --site app.righthire.ae execute right_hire.link_vehicles_to_pi.link_vehicles_to_purchase_invoice --args '["<PI-NAME>"]'
"""

import frappe

def link_vehicles_to_purchase_invoice(pi_name):
    """
    Link the three Nissan Magnite vehicles to their Purchase Invoice

    Args:
        pi_name: The name of the Purchase Invoice (e.g., ACC-PINV-2025-00001)
    """
    frappe.set_user("Administrator")

    print(f"\nLinking vehicles to Purchase Invoice: {pi_name}")
    print("="*60)

    # Check if PI exists
    if not frappe.db.exists("Purchase Invoice", pi_name):
        print(f"✗ Purchase Invoice {pi_name} not found")
        return {"success": False, "message": "Purchase Invoice not found"}

    # Get the Purchase Invoice
    pi = frappe.get_doc("Purchase Invoice", pi_name)
    print(f"✓ Found Purchase Invoice: {pi.name}")
    print(f"  Supplier: {pi.supplier}")
    print(f"  Total: {pi.grand_total} {pi.currency}")

    # The three vehicles
    vehicle_ids = [
        "NIS-MAG-SG023591",
        "NIS-MAG-SG023608",
        "NIS-MAG-SG023673"
    ]

    linked_count = 0

    for vehicle_id in vehicle_ids:
        # Check if vehicle exists
        if not frappe.db.exists("Vehicle", vehicle_id):
            print(f"\n✗ Vehicle {vehicle_id} not found")
            continue

        # Get vehicle
        vehicle = frappe.get_doc("Vehicle", vehicle_id)

        # Update vehicle with purchase invoice reference
        vehicle.db_set("purchase_invoice", pi_name, update_modified=False)

        print(f"\n✓ Linked Vehicle: {vehicle.name}")
        print(f"  Chassis: {vehicle.chassis_number}")
        print(f"  Purchase Invoice: {pi_name}")

        linked_count += 1

    # Also link in the Purchase Invoice items if custom field exists
    try:
        if pi.items and len(pi.items) == 3:
            for i, item_row in enumerate(pi.items):
                if i < len(vehicle_ids):
                    item_row.db_set("vehicle", vehicle_ids[i], update_modified=False)
                    print(f"\n✓ Linked PI Item Row {i+1} to Vehicle {vehicle_ids[i]}")
    except Exception as e:
        print(f"\nNote: Could not link PI items to vehicles (custom field may not exist): {str(e)}")

    frappe.db.commit()

    print(f"\n{'='*60}")
    print(f"✓ LINKING COMPLETED!")
    print(f"  Linked {linked_count} vehicles to Purchase Invoice {pi_name}")
    print(f"{'='*60}\n")

    return {
        "success": True,
        "linked_count": linked_count,
        "purchase_invoice": pi_name,
        "vehicles": vehicle_ids
    }


def show_vehicle_purchase_details():
    """Show purchase details for all three vehicles"""
    frappe.set_user("Administrator")

    vehicle_ids = [
        "NIS-MAG-SG023591",
        "NIS-MAG-SG023608",
        "NIS-MAG-SG023673"
    ]

    print("\nVehicle Purchase Details")
    print("="*80)

    for vehicle_id in vehicle_ids:
        vehicle = frappe.get_doc("Vehicle", vehicle_id)

        print(f"\nVehicle: {vehicle.name}")
        print(f"  Chassis: {vehicle.chassis_number}")
        print(f"  Make/Model: {vehicle.make} {vehicle.model}")
        print(f"  Year: {vehicle.year}")
        print(f"  Purchase Cost: {vehicle.purchase_cost}")
        print(f"  Purchase Date: {vehicle.purchase_date}")
        print(f"  Supplier: {vehicle.supplier}")

        # Check if purchase invoice is linked
        pi_ref = vehicle.get("purchase_invoice")
        if pi_ref:
            print(f"  Purchase Invoice: {pi_ref} ✓")
        else:
            print(f"  Purchase Invoice: Not linked ✗")

    print("\n" + "="*80)
