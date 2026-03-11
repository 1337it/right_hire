"""
Script to add RTA plate fields to Vehicle DocType
Run with: bench --site right_hire.local execute right_hire.right_hire.add_rta_plate_fields.add_fields
"""

import frappe

def add_fields():
	"""Add RTA plate fields to Vehicle DocType"""

	custom_fields = {
		"Vehicle": [
			{
				"fieldname": "section_break_rta_plate",
				"label": "RTA Plate Details",
				"fieldtype": "Section Break",
				"insert_after": "plate_no",
				"collapsible": 1
			},
			{
				"fieldname": "plate_source",
				"label": "Plate Source (Emirate)",
				"fieldtype": "Select",
				"options": "\nDubai\nAbu Dhabi\nSharjah\nAjman\nRas Al Khaimah\nUmm Al Quwain\nFujairah",
				"insert_after": "section_break_rta_plate",
				"description": "Emirate where the plate is registered"
			},
			{
				"fieldname": "plate_category",
				"label": "Plate Category",
				"fieldtype": "Data",
				"default": "Private",
				"insert_after": "plate_source",
				"description": "Vehicle category (default: Private)"
			},
			{
				"fieldname": "column_break_rta",
				"fieldtype": "Column Break",
				"insert_after": "plate_category"
			},
			{
				"fieldname": "plate_code",
				"label": "Plate Code",
				"fieldtype": "Data",
				"insert_after": "column_break_rta",
				"description": "Plate code (e.g., DD, A, 2)"
			},
			{
				"fieldname": "rta_sync_enabled",
				"label": "Enable RTA Fines Sync",
				"fieldtype": "Check",
				"default": "1",
				"insert_after": "plate_code",
				"description": "Auto-sync traffic fines from RTA"
			}
		]
	}

	for doctype, fields in custom_fields.items():
		for field in fields:
			# Check if custom field already exists
			if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]}):
				custom_field = frappe.get_doc({
					"doctype": "Custom Field",
					"dt": doctype,
					**field
				})
				custom_field.insert(ignore_permissions=True)
				frappe.db.commit()
				print(f"✅ Added custom field: {field['fieldname']} to {doctype}")
			else:
				print(f"⚠️  Custom field already exists: {field['fieldname']} in {doctype}")

	print("\n✅ RTA plate fields added successfully!")
	return {"status": "success", "message": "RTA plate fields added successfully"}

if __name__ == "__main__":
	add_fields()
