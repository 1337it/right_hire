"""
Create Fixed Asset records for the 3 Nissan Magnite vehicles
Run with: bench --site app.righthire.ae execute right_hire.create_vehicle_assets.create_vehicle_assets
"""

import frappe
from frappe.utils import nowdate, add_years

def create_vehicle_assets():
    """Create Asset records for the three Nissan Magnite vehicles"""
    frappe.set_user("Administrator")

    print("\n" + "="*60)
    print("Creating Fixed Asset records for Nissan Magnite Vehicles")
    print("="*60)

    # Get or create Asset Category
    asset_category = get_or_create_asset_category()

    # Get company
    company = frappe.defaults.get_defaults().get("company") or "Right Hire Car Rental LLC"

    # The three vehicles
    vehicles = [
        {
            'vehicle_id': 'NIS-MAG-SG023591',
            'chassis': 'MDHBD0FA9SG023591',
        },
        {
            'vehicle_id': 'NIS-MAG-SG023608',
            'chassis': 'MDHBD0FA0SG023608',
        },
        {
            'vehicle_id': 'NIS-MAG-SG023673',
            'chassis': 'MDHBD0FA0SG023673',
        },
    ]

    created_count = 0

    for veh in vehicles:
        print(f"\n{'='*60}")
        print(f"Processing Vehicle: {veh['vehicle_id']}")
        print(f"{'='*60}")

        # Check if asset already exists
        existing = frappe.db.get_value("Asset",
                                       {"asset_name": f"Nissan Magnite - {veh['chassis']}"},
                                       "name")

        if existing:
            print(f"✓ Asset already exists: {existing}")
            continue

        try:
            # Get vehicle data
            vehicle = frappe.get_doc("Vehicle", veh['vehicle_id'])

            # Create Asset
            asset = frappe.get_doc({
                "doctype": "Asset",
                "asset_name": f"Nissan Magnite - {veh['chassis']}",
                "asset_category": asset_category,
                "company": company,
                "item_code": "VEHICLE-NISSAN-MAGNITE",
                "gross_purchase_amount": 47000.00,  # Before tax
                "purchase_date": vehicle.purchase_date or "2025-12-30",
                "available_for_use_date": vehicle.purchase_date or "2025-12-30",
                "is_existing_asset": 0,
                "calculate_depreciation": 1,
                "frequency_of_depreciation": 12,  # Monthly
                "total_number_of_depreciations": 60,  # 5 years
                "expected_value_after_useful_life": 5000,  # Salvage value
                "depreciation_method": "Straight Line",
                "purchase_invoice": vehicle.purchase_invoice,
            })

            asset.insert(ignore_permissions=True)

            print(f"✓ Created Asset: {asset.name}")
            print(f"  Asset Name: {asset.asset_name}")
            print(f"  Purchase Amount: {asset.gross_purchase_amount} AED")
            print(f"  Useful Life: 5 years")
            print(f"  Depreciation Method: Straight Line")
            print(f"  Salvage Value: {asset.expected_value_after_useful_life} AED")

            # Link asset to vehicle (custom field)
            try:
                vehicle.db_set("asset", asset.name, update_modified=False)
                print(f"✓ Linked Asset to Vehicle")
            except:
                print(f"  Note: Could not link asset to vehicle (custom field may not exist)")

            frappe.db.commit()
            created_count += 1

        except Exception as e:
            print(f"✗ Error creating asset: {str(e)}")
            import traceback
            traceback.print_exc()
            frappe.db.rollback()

    print(f"\n{'='*60}")
    print(f"✓ ASSET CREATION COMPLETED!")
    print(f"  Created: {created_count} assets")
    print(f"{'='*60}\n")

    print("\n📊 ASSET SUMMARY:")
    print("Each vehicle is now tracked as a Fixed Asset with:")
    print("  • Gross Purchase Amount: 47,000 AED")
    print("  • Useful Life: 5 years (60 months)")
    print("  • Depreciation: Straight Line")
    print("  • Monthly Depreciation: ~700 AED/month")
    print("  • Salvage Value: 5,000 AED")
    print("\nTo activate depreciation:")
    print("  1. Go to each Asset record")
    print("  2. Click 'Submit' to activate")
    print("  3. Depreciation will be calculated automatically\n")

    return {
        "success": True,
        "created_count": created_count,
        "asset_category": asset_category
    }


def get_or_create_asset_category():
    """Get or create Vehicles asset category"""

    category_name = "Vehicles"

    # Check if category exists
    if frappe.db.exists("Asset Category", category_name):
        print(f"\n✓ Using existing Asset Category: {category_name}")
        return category_name

    print(f"\n📁 Creating Asset Category: {category_name}")

    try:
        # Get company
        company = frappe.defaults.get_defaults().get("company") or "Right Hire Car Rental LLC"

        # Get accounts
        fixed_asset_account = frappe.db.get_value("Account",
            {"account_type": "Fixed Asset", "company": company, "is_group": 0},
            "name")

        accumulated_dep_account = frappe.db.get_value("Account",
            {"account_type": "Accumulated Depreciation", "company": company},
            "name")

        depreciation_expense_account = frappe.db.get_value("Account",
            {"account_type": "Depreciation", "company": company},
            "name")

        print(f"  Fixed Asset Account: {fixed_asset_account}")
        print(f"  Accumulated Depreciation: {accumulated_dep_account}")
        print(f"  Depreciation Expense: {depreciation_expense_account}")

        # Create category
        category = frappe.get_doc({
            "doctype": "Asset Category",
            "asset_category_name": category_name,
            "enable_cwip_accounting": 0,
        })

        # Add company-specific accounts
        category.append("accounts", {
            "company_name": company,
            "fixed_asset_account": fixed_asset_account,
            "accumulated_depreciation_account": accumulated_dep_account,
            "depreciation_expense_account": depreciation_expense_account,
        })

        category.insert(ignore_permissions=True)
        frappe.db.commit()

        print(f"✓ Created Asset Category: {category.name}\n")
        return category.name

    except Exception as e:
        print(f"✗ Error creating asset category: {str(e)}")
        import traceback
        traceback.print_exc()
        frappe.db.rollback()
        return None
