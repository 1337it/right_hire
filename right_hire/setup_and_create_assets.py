"""
Complete Asset Setup for Vehicles
Run with: bench --site app.righthire.ae execute right_hire.setup_and_create_assets.setup_and_create_all_assets
"""

import frappe
from frappe.utils import nowdate, add_months, add_days, getdate

def setup_and_create_all_assets():
    """Complete setup: Item, Asset Category, and create Assets"""
    frappe.set_user("Administrator")

    print("\n" + "="*70)
    print("COMPLETE VEHICLE ASSET SETUP")
    print("="*70)

    # Step 1: Setup Asset Category
    asset_category = setup_asset_category()
    if not asset_category:
        return {"success": False, "message": "Failed to create Asset Category"}

    # Step 2: Update Item to be Fixed Asset
    update_item_as_fixed_asset(asset_category)

    # Step 3: Create Assets manually (since PI already exists)
    created_assets = create_assets_for_vehicles(asset_category)

    print("\n" + "="*70)
    print("✅ SETUP COMPLETED!")
    print("="*70)
    print(f"\nCreated {len(created_assets)} Asset records")
    print("\n📌 IMPORTANT: You must now:")
    print("   1. Go to each Asset record")
    print("   2. Review the depreciation schedule")
    print("   3. Click 'Submit' to activate")
    print("   4. Monthly depreciation will auto-post via scheduler\n")

    return {
        "success": True,
        "asset_category": asset_category,
        "created_assets": created_assets
    }


def setup_asset_category():
    """Setup Vehicles Asset Category with proper accounts"""

    category_name = "Vehicles"

    if frappe.db.exists("Asset Category", category_name):
        print(f"\n✓ Asset Category '{category_name}' already exists")
        return category_name

    print(f"\n📁 Creating Asset Category: {category_name}")

    company = frappe.defaults.get_defaults().get("company") or "Right Hire Car Rental LLC"

    # Get required accounts
    accounts = get_asset_accounts(company)

    if not all(accounts.values()):
        print("✗ Could not find all required accounts")
        return None

    print(f"  Fixed Asset Account: {accounts['fixed_asset']}")
    print(f"  Accumulated Depreciation: {accounts['accumulated_depreciation']}")
    print(f"  Depreciation Expense: {accounts['depreciation_expense']}")

    try:
        category = frappe.get_doc({
            "doctype": "Asset Category",
            "asset_category_name": category_name,
            "enable_cwip_accounting": 0,
        })

        category.append("accounts", {
            "company_name": company,
            "fixed_asset_account": accounts['fixed_asset'],
            "accumulated_depreciation_account": accounts['accumulated_depreciation'],
            "depreciation_expense_account": accounts['depreciation_expense'],
        })

        category.insert(ignore_permissions=True)
        frappe.db.commit()

        print(f"✓ Created Asset Category: {category.name}")
        return category.name

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        frappe.db.rollback()
        return None


def get_asset_accounts(company):
    """Get or find appropriate asset accounts"""

    accounts = {}

    # Fixed Asset Account
    accounts['fixed_asset'] = frappe.db.get_value("Account",
        {"company": company, "account_type": "Fixed Asset", "is_group": 0},
        "name")

    # Accumulated Depreciation Account
    accounts['accumulated_depreciation'] = frappe.db.get_value("Account",
        {"company": company, "account_type": "Accumulated Depreciation"},
        "name")

    # Depreciation Expense Account
    accounts['depreciation_expense'] = frappe.db.get_value("Account",
        {"company": company, "account_type": "Depreciation"},
        "name")

    return accounts


def update_item_as_fixed_asset(asset_category):
    """Update Vehicle Item to be a Fixed Asset"""

    item_code = "VEHICLE-NISSAN-MAGNITE"

    print(f"\n🔧 Configuring Item: {item_code}")

    if not frappe.db.exists("Item", item_code):
        print(f"✗ Item not found: {item_code}")
        return False

    try:
        item = frappe.get_doc("Item", item_code)

        # Update to be fixed asset
        item.is_fixed_asset = 1
        item.asset_category = asset_category
        item.auto_create_assets = 1  # Auto-create from Purchase Invoice

        item.save(ignore_permissions=True)
        frappe.db.commit()

        print(f"✓ Item configured as Fixed Asset")
        print(f"  Asset Category: {asset_category}")
        print(f"  Auto Create Assets: Yes")

        return True

    except Exception as e:
        print(f"✗ Error updating item: {str(e)}")
        frappe.db.rollback()
        return False


def get_or_create_location(location_name):
    """Get or create a location for assets"""

    if frappe.db.exists("Location", location_name):
        return location_name

    try:
        loc = frappe.get_doc({
            "doctype": "Location",
            "location_name": location_name,
        })
        loc.insert(ignore_permissions=True)
        frappe.db.commit()
        return loc.name
    except:
        # If fails, try to get any location
        existing = frappe.db.get_value("Location", {}, "name")
        if existing:
            return existing
        # Last resort: create a default location
        try:
            loc = frappe.get_doc({
                "doctype": "Location",
                "location_name": "Main Office",
            })
            loc.insert(ignore_permissions=True)
            frappe.db.commit()
            return loc.name
        except:
            return "Main Office"


def create_assets_for_vehicles(asset_category):
    """Create Asset records for the three vehicles"""

    print(f"\n🏗️  Creating Asset Records")
    print("="*70)

    company = frappe.defaults.get_defaults().get("company") or "Right Hire Car Rental LLC"

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

    created_assets = []

    for veh in vehicles:
        print(f"\n📦 Vehicle: {veh['vehicle_id']}")

        # Check if asset exists
        existing = frappe.db.get_value("Asset",
            {"asset_name": f"Nissan Magnite - {veh['chassis']}"},
            "name")

        if existing:
            print(f"  ✓ Asset already exists: {existing}")
            created_assets.append(existing)
            continue

        try:
            vehicle = frappe.get_doc("Vehicle", veh['vehicle_id'])

            # Get or create location
            location = get_or_create_location(vehicle.branch if hasattr(vehicle, 'branch') else "Main")

            # Create Asset
            asset = frappe.get_doc({
                "doctype": "Asset",
                "asset_name": f"Nissan Magnite - {veh['chassis']}",
                "asset_category": asset_category,
                "item_code": "VEHICLE-NISSAN-MAGNITE",
                "company": company,
                "location": location,
                "purchase_date": vehicle.purchase_date or "2025-12-30",
                "available_for_use_date": vehicle.purchase_date or "2025-12-30",
                "gross_purchase_amount": 47000.00,
                "purchase_receipt_amount": 47000.00,
                "is_existing_asset": 0,
                "calculate_depreciation": 1,
                "opening_accumulated_depreciation": 0,
                "number_of_depreciations_booked": 0,
            })

            # Add depreciation schedule in finance_books
            asset.append("finance_books", {
                "finance_book": None,  # Default finance book
                "depreciation_method": "Straight Line",
                "total_number_of_depreciations": 60,  # 5 years monthly
                "frequency_of_depreciation": 12,  # Monthly
                "depreciation_start_date": add_months(getdate(vehicle.purchase_date or "2025-12-30"), 1),
                "expected_value_after_useful_life": 5000.00,  # Salvage value
            })

            asset.insert(ignore_permissions=True)
            frappe.db.commit()  # Commit asset first

            print(f"  ✓ Created Asset: {asset.name}")
            print(f"    Purchase Amount: {asset.gross_purchase_amount:,.2f} AED")
            print(f"    Useful Life: 5 years (60 months)")
            print(f"    Depreciation: ~{(asset.gross_purchase_amount - 5000)/60:,.2f} AED/month")
            print(f"    Salvage Value: {asset.finance_books[0].expected_value_after_useful_life:,.2f} AED")

            # Link to PI if available
            if vehicle.purchase_invoice:
                try:
                    asset.db_set("purchase_invoice", vehicle.purchase_invoice, update_modified=False)
                    frappe.db.commit()
                    print(f"    Linked to PI: {vehicle.purchase_invoice}")
                except:
                    pass

            created_assets.append(asset.name)

        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            frappe.db.rollback()

    return created_assets


def show_asset_summary():
    """Display summary of created assets"""

    print("\n" + "="*70)
    print("📊 ASSET SUMMARY")
    print("="*70)

    assets = frappe.get_all("Asset",
        filters={"asset_category": "Vehicles"},
        fields=["name", "asset_name", "gross_purchase_amount", "docstatus"],
        order_by="creation desc")

    if not assets:
        print("\n No assets found")
        return

    total_value = 0

    for asset in assets:
        status = "✅ Active" if asset.docstatus == 1 else "📝 Draft"
        print(f"\n{asset.name}")
        print(f"  Name: {asset.asset_name}")
        print(f"  Value: {asset.gross_purchase_amount:,.2f} AED")
        print(f"  Status: {status}")
        total_value += asset.gross_purchase_amount

    print(f"\n{'='*70}")
    print(f"Total Fleet Value: {total_value:,.2f} AED")
    print(f"{'='*70}\n")
