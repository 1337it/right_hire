"""Update Lease Quotation DocType structure - remove vehicle and pricing sections, add quotation items table"""
import frappe
import json

def update_lease_quotation():
    """Update Lease Quotation DocType"""

    # Load the DocType
    doctype_path = "/home/frappe/frappe-bench/apps/right_hire/right_hire/right_hire/doctype/lease_quotation/lease_quotation.json"

    with open(doctype_path, 'r') as f:
        doc = json.load(f)

    # Fields to remove from field_order
    fields_to_remove = [
        "vehicle_section",
        "vehicle_category",
        "vehicle",
        "vehicle_details",
        "column_break_vehicle",
        "preferred_make",
        "preferred_model",
        "pricing_section",
        "rate_plan",
        "monthly_rate",
        "total_amount",
        "column_break_pricing",
        "deposit_amount",
        "maintenance_included",
        "insurance_included"
    ]

    # Remove from field_order
    doc["field_order"] = [f for f in doc["field_order"] if f not in fields_to_remove]

    # Add quotation_items section after lease_details_section
    lease_idx = doc["field_order"].index("traffic_fines_amount")
    doc["field_order"].insert(lease_idx + 1, "quotation_items_section")
    doc["field_order"].insert(lease_idx + 2, "quotation_items")

    # Remove field definitions
    doc["fields"] = [f for f in doc["fields"] if f.get("fieldname") not in fields_to_remove]

    # Find index to insert new fields (after traffic_fines_amount)
    insert_idx = None
    for i, field in enumerate(doc["fields"]):
        if field.get("fieldname") == "traffic_fines_amount":
            insert_idx = i + 1
            break

    # Add new fields
    new_fields = [
        {
            "fieldname": "quotation_items_section",
            "fieldtype": "Section Break",
            "label": "Vehicle Options"
        },
        {
            "fieldname": "quotation_items",
            "fieldtype": "Table",
            "label": "Quotation Items",
            "options": "Lease Quotation Item",
            "reqd": 1
        }
    ]

    if insert_idx is not None:
        for i, field in enumerate(new_fields):
            doc["fields"].insert(insert_idx + i, field)
    else:
        doc["fields"].extend(new_fields)

    # Update modified timestamp
    from frappe.utils import now
    doc["modified"] = now()

    # Save back to file
    with open(doctype_path, 'w') as f:
        json.dump(doc, f, indent=1)

    print(f"✓ Updated Lease Quotation DocType JSON")
    print(f"  - Removed {len(fields_to_remove)} fields")
    print(f"  - Added quotation_items table")

    return doc

if __name__ == "__main__":
    frappe.init(site="app.righthire.ae")
    frappe.connect()

    update_lease_quotation()

    print("\n✓ Now run: bench --site app.righthire.ae migrate")
