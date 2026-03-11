import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, cstr, now_datetime
from datetime import datetime, timedelta


@frappe.whitelist()
def get_active_agreement_for_vehicle_at_date(vehicle, date, time=None):
    """
    Determine which agreement (if any) a vehicle was under at a specific date/time.
    This is crucial for attributing fines/tolls to the correct customer.

    Logic:
    1. Check if there's a Lease Agreement active on that date
    2. Check if there's a Rental Agreement active on that date
    3. Check movements to see if vehicle was with customer at that time
    """
    check_date = getdate(date)

    # Build datetime for more precise checking if time is provided
    if time:
        try:
            check_datetime = get_datetime(f"{date} {time}")
        except:
            check_datetime = get_datetime(date)
    else:
        check_datetime = get_datetime(date)

    # First, check Lease Agreements
    lease_agreements = frappe.get_all(
        "Lease Agreement",
        filters={
            "vehicle": vehicle,
            "start_date": ["<=", check_date],
            "docstatus": ["!=", 2]  # Not cancelled
        },
        fields=["name", "customer", "customer_name", "start_date", "end_date", "lease_status"],
        order_by="start_date desc"
    )

    for la in lease_agreements:
        # Check if agreement was active on that date
        end_date = la.end_date or getdate("2099-12-31")  # If no end date, assume ongoing
        if la.start_date <= check_date <= end_date:
            # Check if status was active (not terminated before this date)
            if la.lease_status in ["Active", "Draft", "Under Notice"]:
                # Check movements to see if vehicle was out to customer
                if was_vehicle_with_customer(vehicle, check_datetime, "Lease Agreement", la.name):
                    return {
                        "agreement_type": "Lease Agreement",
                        "agreement_name": la.name,
                        "customer": la.customer,
                        "customer_name": la.customer_name,
                        "start_date": cstr(la.start_date),
                        "end_date": cstr(la.end_date) if la.end_date else None
                    }

    # Then check Rental Agreements
    rental_agreements = frappe.get_all(
        "Rental Agreement",
        filters={
            "vehicle": vehicle,
            "docstatus": ["!=", 2]
        },
        fields=["name", "customer", "customer_name", "start_datetime", "end_datetime", "actual_return_datetime", "agreement_status"],
        order_by="creation desc"
    )

    for ra in rental_agreements:
        start_date = getdate(ra.start_datetime) if ra.start_datetime else None
        end_date = getdate(ra.actual_return_datetime or ra.end_datetime) if (ra.actual_return_datetime or ra.end_datetime) else getdate("2099-12-31")
        if start_date and start_date <= check_date <= end_date:
            if ra.agreement_status in ["Active", "Draft", "Extended"]:
                if was_vehicle_with_customer(vehicle, check_datetime, "Rental Agreement", ra.name):
                    return {
                        "agreement_type": "Rental Agreement",
                        "agreement_name": ra.name,
                        "customer": ra.customer,
                        "customer_name": ra.customer_name,
                        "start_date": cstr(ra.start_datetime)[:10] if ra.start_datetime else None,
                        "end_date": cstr(ra.end_datetime)[:10] if ra.end_datetime else None
                    }

    # Check Lease to Own
    lease_to_own = frappe.get_all(
        "Lease to Own",
        filters={
            "vehicle": vehicle,
            "start_date": ["<=", check_date],
            "docstatus": ["!=", 2]
        },
        fields=["name", "customer", "customer_name", "start_date", "end_date", "status"],
        order_by="start_date desc"
    )

    for lto in lease_to_own:
        end_date = lto.end_date or getdate("2099-12-31")
        if lto.start_date <= check_date <= end_date:
            if lto.status in ["Active", "Draft"]:
                return {
                    "agreement_type": "Lease to Own",
                    "agreement_name": lto.name,
                    "customer": lto.customer,
                    "customer_name": lto.customer_name,
                    "start_date": cstr(lto.start_date),
                    "end_date": cstr(lto.end_date) if lto.end_date else None
                }

    return None


def was_vehicle_with_customer(vehicle, check_datetime, agreement_type=None, agreement_name=None):
    """
    Check movement history to determine if vehicle was with customer at given datetime.

    Returns True if:
    - Vehicle had an OUT movement before the check_datetime
    - AND no IN (return) movement before the check_datetime after the OUT
    """
    # Get the most recent OUT movement before check_datetime
    filters = {
        "vehicle": vehicle,
        "out_date_time": ["<=", check_datetime],
        "status": ["in", ["Out Only", "Completed", "In Transit"]]
    }

    if agreement_type and agreement_name:
        filters["agreement_type"] = agreement_type
        filters["agreement_no"] = agreement_name

    out_movement = frappe.get_all(
        "Movements",
        filters=filters,
        fields=["name", "out_date_time", "in_date_time", "status"],
        order_by="out_date_time desc",
        limit=1
    )

    if not out_movement:
        # No out movement found - could still be with customer if agreement is active
        # Default to True if agreement exists, since delivery might have happened
        return True if agreement_type and agreement_name else False

    out_mov = out_movement[0]

    # If the out movement has an in_date_time, check if vehicle was returned before check_datetime
    if out_mov.in_date_time:
        if get_datetime(out_mov.in_date_time) <= check_datetime:
            # Vehicle was returned before the check time
            return False

    # Vehicle was out and not returned yet at check_datetime
    return True


@frappe.whitelist()
def get_vehicle_status_at_date(vehicle, date, time=None):
    """
    Get the status of a vehicle at a specific date/time based on status log history.
    """
    check_datetime = get_datetime(f"{date} {time}") if time else get_datetime(date)

    # Get the most recent status log entry before or at the check datetime
    status_log = frappe.get_all(
        "Vehicle Status Log",
        filters={
            "vehicle": vehicle,
            "changed_at": ["<=", check_datetime]
        },
        fields=["name", "from_status", "to_status", "changed_at", "reason", "reference_doctype", "reference_name"],
        order_by="changed_at desc",
        limit=1
    )

    if status_log:
        return {
            "status": status_log[0].to_status,
            "changed_at": cstr(status_log[0].changed_at),
            "reason": status_log[0].reason,
            "reference_doctype": status_log[0].reference_doctype,
            "reference_name": status_log[0].reference_name
        }

    # If no log found, get current vehicle status (might be first status ever)
    vehicle_doc = frappe.get_doc("Vehicle", vehicle)
    return {
        "status": vehicle_doc.status,
        "changed_at": None,
        "reason": "Initial status",
        "reference_doctype": None,
        "reference_name": None
    }


@frappe.whitelist()
def attribute_fine_to_agreement(fine_doctype, fine_name):
    """
    Attribute a traffic fine to the correct agreement based on fine date/time.
    """
    fine = frappe.get_doc(fine_doctype, fine_name)

    if not fine.vehicle:
        return {"success": False, "message": "No vehicle linked to fine"}

    # Parse fine date - could be in different formats
    fine_date = None
    fine_time = None

    if hasattr(fine, 'fine_date'):
        fine_date = fine.fine_date
    elif hasattr(fine, 'transaction_date'):
        fine_date = fine.transaction_date

    if hasattr(fine, 'fine_time'):
        fine_time = fine.fine_time
    elif hasattr(fine, 'transaction_time'):
        fine_time = fine.transaction_time

    if not fine_date:
        return {"success": False, "message": "No date found on fine"}

    # Get active agreement at time of fine
    agreement = get_active_agreement_for_vehicle_at_date(fine.vehicle, fine_date, fine_time)

    if agreement:
        # Update the fine with agreement info
        if agreement["agreement_type"] == "Lease Agreement":
            fine.linked_contract = agreement["agreement_name"]
            fine.lease_agreement = agreement["agreement_name"]
        elif agreement["agreement_type"] == "Rental Agreement":
            fine.linked_agreement = agreement["agreement_name"]

        fine.save()

        return {
            "success": True,
            "agreement_type": agreement["agreement_type"],
            "agreement_name": agreement["agreement_name"],
            "customer": agreement["customer"],
            "customer_name": agreement["customer_name"]
        }

    return {
        "success": False,
        "message": "No active agreement found for vehicle at the time of fine"
    }


@frappe.whitelist()
def bulk_attribute_fines(doctype, filters=None):
    """
    Bulk attribute fines/tolls to agreements.
    """
    if filters:
        import json
        filters = json.loads(filters) if isinstance(filters, str) else filters
    else:
        filters = {}

    # Add filter to only process unlinked items
    filters["linked_contract"] = ["is", "not set"]
    filters["linked_agreement"] = ["is", "not set"]

    items = frappe.get_all(doctype, filters=filters, pluck="name", limit=100)

    results = {"attributed": 0, "not_attributed": 0, "errors": []}

    for item_name in items:
        try:
            result = attribute_fine_to_agreement(doctype, item_name)
            if result.get("success"):
                results["attributed"] += 1
            else:
                results["not_attributed"] += 1
        except Exception as e:
            results["errors"].append({"name": item_name, "error": str(e)})

    return results


@frappe.whitelist()
def get_vehicle_fines_tolls(vehicle, page=1, page_len=20):
    """
    Get all fines and tolls for a vehicle with pagination.
    """
    start = (int(page) - 1) * int(page_len)

    # Get Salik transactions
    salik = frappe.get_all(
        "Salik Transaction",
        filters={"vehicle": vehicle},
        fields=[
            "name", "transaction_date as date", "transaction_time as time",
            "gate_location as location", "toll_amount as amount", "status",
            "linked_contract", "linked_agreement", "charged_to_customer"
        ],
        order_by="transaction_date desc"
    )
    for s in salik:
        s["type"] = "Salik"
        s["doctype"] = "Salik Transaction"

    # Get Darb transactions
    darb = frappe.get_all(
        "Darb Transaction",
        filters={"vehicle": vehicle},
        fields=[
            "name", "transaction_date as date", "transaction_time as time",
            "gate_location as location", "toll_amount as amount", "status",
            "linked_contract", "linked_agreement", "charged_to_customer"
        ],
        order_by="transaction_date desc"
    )
    for d in darb:
        d["type"] = "Darb"
        d["doctype"] = "Darb Transaction"

    # Get Traffic fines
    fines = frappe.get_all(
        "Traffic Fine",
        filters={"vehicle": vehicle},
        fields=[
            "name", "fine_date as date", "fine_time as time",
            "location", "amount", "paid as status",
            "linked_contract", "linked_agreement", "charged_to_customer",
            "details", "source"
        ],
        order_by="fine_date desc"
    )
    for f in fines:
        f["type"] = "Traffic Fine"
        f["doctype"] = "Traffic Fine"
        f["status"] = "Paid" if f["status"] else "Unpaid"

    # Combine and sort by date
    all_items = salik + darb + fines
    all_items.sort(key=lambda x: str(x.get("date") or ""), reverse=True)

    total = len(all_items)
    paginated = all_items[start:start + int(page_len)]

    return {"data": paginated, "total": total}


@frappe.whitelist()
def get_agreement_fines_tolls(agreement_type, agreement_no, page=1, page_len=20):
    """
    Get all fines and tolls linked to a specific agreement.
    """
    start = (int(page) - 1) * int(page_len)

    # Determine filter field based on agreement type
    if agreement_type == "Lease Agreement":
        filter_field = "linked_contract"
    else:
        filter_field = "linked_agreement"

    # Get Salik transactions
    salik = frappe.get_all(
        "Salik Transaction",
        filters={filter_field: agreement_no},
        fields=[
            "name", "vehicle", "transaction_date as date", "transaction_time as time",
            "gate_location as location", "toll_amount as amount", "status",
            "charged_to_customer"
        ],
        order_by="transaction_date desc"
    )
    for s in salik:
        s["type"] = "Salik"
        s["doctype"] = "Salik Transaction"

    # Get Darb transactions
    darb = frappe.get_all(
        "Darb Transaction",
        filters={filter_field: agreement_no},
        fields=[
            "name", "vehicle", "transaction_date as date", "transaction_time as time",
            "gate_location as location", "toll_amount as amount", "status",
            "charged_to_customer"
        ],
        order_by="transaction_date desc"
    )
    for d in darb:
        d["type"] = "Darb"
        d["doctype"] = "Darb Transaction"

    # Get Traffic fines
    fines = frappe.get_all(
        "Traffic Fine",
        filters={filter_field: agreement_no},
        fields=[
            "name", "vehicle", "fine_date as date", "fine_time as time",
            "location", "amount", "paid as status",
            "charged_to_customer", "details", "source"
        ],
        order_by="fine_date desc"
    )
    for f in fines:
        f["type"] = "Traffic Fine"
        f["doctype"] = "Traffic Fine"
        f["status"] = "Paid" if f["status"] else "Unpaid"

    # Combine and sort by date
    all_items = salik + darb + fines
    all_items.sort(key=lambda x: str(x.get("date") or ""), reverse=True)

    total = len(all_items)
    paginated = all_items[start:start + int(page_len)]

    # Calculate totals
    total_salik = sum(s.get("amount") or 0 for s in salik)
    total_darb = sum(d.get("amount") or 0 for d in darb)
    total_fines = sum(f.get("amount") or 0 for f in fines)

    return {
        "data": paginated,
        "total": total,
        "summary": {
            "salik_count": len(salik),
            "salik_total": total_salik,
            "darb_count": len(darb),
            "darb_total": total_darb,
            "fines_count": len(fines),
            "fines_total": total_fines,
            "grand_total": total_salik + total_darb + total_fines
        }
    }


@frappe.whitelist()
def get_vehicle_status_history(vehicle):
    """
    Get complete status history for a vehicle.
    """
    history = frappe.get_all(
        "Vehicle Status Log",
        filters={"vehicle": vehicle},
        fields=[
            "name", "from_status", "to_status", "changed_at", "changed_by",
            "reason", "reference_doctype", "reference_name"
        ],
        order_by="changed_at desc"
    )

    return history
