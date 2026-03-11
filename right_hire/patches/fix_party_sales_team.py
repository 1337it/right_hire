"""
Monkey-patch to fix ERPNext party.py sales_team issue.
The issue is that party.get("sales_team") returns None instead of an empty list
when the Customer doesn't have a sales_team child table.
"""
import frappe

def apply_patch(bootinfo=None):
    """Apply monkey patch to fix sales_team None issue"""
    try:
        from erpnext.accounts import party

        # Store original function
        original_get_party_details = party._get_party_details

        def patched_get_party_details(
            party,
            account=None,
            party_type="Customer",
            company=None,
            posting_date=None,
            bill_date=None,
            price_list=None,
            currency=None,
            doctype=None,
            ignore_permissions=False,
            fetch_payment_terms_template=True,
            party_address=None,
            company_address=None,
            shipping_address=None,
            dispatch_address=None,
            pos_profile=None,
        ):
            # Ensure party has sales_team as empty list if None
            if party_type == "Customer" and party:
                if hasattr(party, 'get') and party.get("sales_team") is None:
                    party.sales_team = []
                elif isinstance(party, str):
                    # If party is just a name string, let the original function handle it
                    pass

            return original_get_party_details(
                party,
                account=account,
                party_type=party_type,
                company=company,
                posting_date=posting_date,
                bill_date=bill_date,
                price_list=price_list,
                currency=currency,
                doctype=doctype,
                ignore_permissions=ignore_permissions,
                fetch_payment_terms_template=fetch_payment_terms_template,
                party_address=party_address,
                company_address=company_address,
                shipping_address=shipping_address,
                dispatch_address=dispatch_address,
                pos_profile=pos_profile,
            )

        # Apply the patch
        party._get_party_details = patched_get_party_details
        frappe.logger().info("Applied sales_team monkey patch to erpnext.accounts.party")

    except Exception as e:
        frappe.logger().error(f"Failed to apply sales_team patch: {e}")
