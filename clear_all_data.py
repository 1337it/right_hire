#!/usr/bin/env python3
"""Script to delete all data from all doctypes while keeping the structure."""

import frappe
from frappe.utils import cint

def clear_all_data():
    """Delete all records from all doctypes."""
    frappe.connect()

    # Get all doctypes
    all_doctypes = frappe.get_all('DocType',
        filters={'issingle': 0, 'istable': 0},
        fields=['name', 'module'],
        order_by='creation desc'
    )

    print(f"\nFound {len(all_doctypes)} doctypes to clear")

    # Skip system/core doctypes
    skip_modules = ['Core', 'Desk', 'Email', 'Printing', 'Website', 'Workflow',
                    'Custom', 'Integrations', 'Automation', 'Social', 'Geo']

    skip_doctypes = ['User', 'Role', 'Module Def', 'DocType', 'DocField',
                     'Print Format', 'Report', 'Page', 'Web Form', 'Web Page',
                     'Error Log', 'Version', 'Activity Log', 'Comment',
                     'Custom Field', 'Property Setter', 'Client Script',
                     'Server Script', 'Scheduled Job Type', 'Scheduled Job Log']

    deleted_count = 0

    for dt in all_doctypes:
        doctype = dt.name

        # Skip system doctypes
        if dt.module in skip_modules or doctype in skip_doctypes:
            continue

        try:
            # Get all records for this doctype
            records = frappe.get_all(doctype, pluck='name')

            if records:
                print(f"\nDeleting {len(records)} records from {doctype}...")

                # Delete each record
                for name in records:
                    try:
                        frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
                        deleted_count += 1
                    except Exception as e:
                        print(f"  Error deleting {doctype} {name}: {str(e)}")

                frappe.db.commit()
                print(f"  ✓ Deleted {len(records)} records from {doctype}")

        except Exception as e:
            print(f"  Error processing {doctype}: {str(e)}")
            continue

    print(f"\n\n{'='*60}")
    print(f"Data deletion complete!")
    print(f"Total records deleted: {deleted_count}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    clear_all_data()
