import frappe
from frappe import _
from frappe.utils import now_datetime, getdate, cstr


@frappe.whitelist()
def get_vehicle_movements(vehicle, from_date=None, to_date=None, movement_type=None, page=1, page_len=10):
    """Get movements for a vehicle with pagination and filters"""
    filters = {"vehicle": vehicle}

    if from_date:
        filters["date"] = [">=", from_date]
    if to_date:
        if "date" in filters:
            filters["date"] = ["between", [from_date, to_date]]
        else:
            filters["date"] = ["<=", to_date]
    if movement_type:
        filters["movement_type"] = ["like", f"%{movement_type}%"]

    # Get total count
    total = frappe.db.count("Movements", filters)

    # Get paginated data
    start = (int(page) - 1) * int(page_len)
    data = frappe.get_all(
        "Movements",
        filters=filters,
        fields=[
            "name", "movement_id", "movement_type", "date", "status",
            "out_date_time", "in_date_time", "out_from", "in_to", "drop_location",
            "out_mileage", "in_mileage", "odometer_value", "unit",
            "out_driver", "in_driver", "out_customer", "in_customer",
            "out_staff", "in_staff", "out_notes", "in_notes",
            "agreement_type", "agreement_no"
        ],
        order_by="date desc, creation desc",
        start=start,
        page_length=int(page_len)
    )

    return {"data": data, "total": total}


@frappe.whitelist()
def get_vehicle_timeline(vehicle):
    """Get timeline data for a vehicle including agreements and movements"""
    timeline = []

    # Get vehicle info
    vehicle_doc = frappe.get_doc("Vehicle", vehicle)

    # Add vehicle purchase/registration as first event
    if vehicle_doc.purchase_date:
        timeline.append({
            "date": cstr(vehicle_doc.purchase_date),
            "type": "purchase",
            "title": "Vehicle Purchased",
            "subtitle": f"AED {vehicle_doc.purchase_cost:,.0f}" if vehicle_doc.purchase_cost else None,
            "color": "blue"
        })

    # Get all Lease Agreements for this vehicle
    lease_agreements = frappe.get_all(
        "Lease Agreement",
        filters={"vehicle": vehicle},
        fields=["name", "customer_name", "start_date", "end_date", "lease_status", "creation"],
        order_by="start_date asc"
    )

    for la in lease_agreements:
        timeline.append({
            "date": cstr(la.start_date) if la.start_date else cstr(la.creation)[:10],
            "type": "lease_start",
            "title": "Lease Started",
            "subtitle": la.customer_name,
            "link": f"/app/lease-agreement/{la.name}",
            "ref": la.name,
            "color": "green"
        })
        if la.end_date and la.lease_status in ["Completed", "Terminated", "Cancelled"]:
            timeline.append({
                "date": cstr(la.end_date),
                "type": "lease_end",
                "title": f"Lease {la.lease_status}",
                "subtitle": la.customer_name,
                "link": f"/app/lease-agreement/{la.name}",
                "ref": la.name,
                "color": "gray"
            })

    # Get all Rental Agreements for this vehicle
    rental_agreements = frappe.get_all(
        "Rental Agreement",
        filters={"vehicle": vehicle},
        fields=["name", "customer_name", "start_datetime", "end_datetime", "actual_return_datetime", "agreement_status", "creation"],
        order_by="creation asc"
    )

    for ra in rental_agreements:
        start_date = cstr(ra.start_datetime)[:10] if ra.start_datetime else cstr(ra.creation)[:10]
        timeline.append({
            "date": start_date,
            "type": "rental_start",
            "title": "Rental Started",
            "subtitle": ra.customer_name,
            "link": f"/app/rental-agreement/{ra.name}",
            "ref": ra.name,
            "color": "orange"
        })
        end_date = ra.actual_return_datetime or ra.end_datetime
        if end_date and ra.agreement_status in ["Completed", "Closed", "Cancelled", "Returned"]:
            timeline.append({
                "date": cstr(end_date)[:10],
                "type": "rental_end",
                "title": f"Rental {ra.agreement_status}",
                "subtitle": ra.customer_name,
                "link": f"/app/rental-agreement/{ra.name}",
                "ref": ra.name,
                "color": "gray"
            })

    # Get movements
    movements = frappe.get_all(
        "Movements",
        filters={"vehicle": vehicle},
        fields=["name", "movement_type", "date", "status", "out_customer", "in_customer", "agreement_no"],
        order_by="date asc",
        limit=50
    )

    for mov in movements:
        color = "blue"
        if "Delivery" in (mov.movement_type or ""):
            color = "purple"
        elif "Workshop" in (mov.movement_type or ""):
            color = "red"
        elif "Custody" in (mov.movement_type or ""):
            color = "yellow"
        elif "Recovery" in (mov.movement_type or ""):
            color = "orange"

        customer = mov.out_customer or mov.in_customer or ""
        timeline.append({
            "date": cstr(mov.date),
            "type": "movement",
            "title": mov.movement_type,
            "subtitle": customer or mov.agreement_no or mov.status,
            "link": f"/app/movements/{mov.name}",
            "ref": mov.name,
            "color": color
        })

    # Sort by date
    timeline.sort(key=lambda x: x.get("date", ""))

    return timeline


@frappe.whitelist()
def get_agreement_movements(agreement_type, agreement_no, page=1, page_len=10):
    """Get movements for an agreement with pagination"""
    filters = {
        "agreement_type": agreement_type,
        "agreement_no": agreement_no
    }

    # Get total count
    total = frappe.db.count("Movements", filters)

    # Get paginated data
    start = (int(page) - 1) * int(page_len)
    data = frappe.get_all(
        "Movements",
        filters=filters,
        fields=[
            "name", "movement_id", "movement_type", "date", "status",
            "out_date_time", "in_date_time", "vehicle",
            "out_mileage", "in_mileage",
            "out_driver", "in_driver", "out_customer", "in_customer",
            "out_staff", "in_staff", "out_notes", "in_notes"
        ],
        order_by="date desc, creation desc",
        start=start,
        page_length=int(page_len)
    )

    return {"data": data, "total": total}


@frappe.whitelist()
def get_agreement_timeline(agreement_type, agreement_no):
    """Get timeline data for an agreement"""
    timeline = []

    # Get agreement details
    agreement = frappe.get_doc(agreement_type, agreement_no)

    # Add quotation if exists
    if hasattr(agreement, 'quotation') and agreement.quotation:
        try:
            quotation = frappe.get_doc("Lease Quotation", agreement.quotation)
            timeline.append({
                "date": cstr(quotation.creation)[:10],
                "type": "quotation",
                "title": "Quotation Created",
                "subtitle": quotation.name,
                "link": f"/app/lease-quotation/{quotation.name}",
                "color": "blue"
            })
        except:
            pass

    # Agreement creation
    timeline.append({
        "date": cstr(agreement.creation)[:10],
        "type": "created",
        "title": "Agreement Created",
        "subtitle": agreement.vehicle,
        "color": "blue"
    })

    # Agreement start
    if hasattr(agreement, 'start_date') and agreement.start_date:
        timeline.append({
            "date": cstr(agreement.start_date),
            "type": "started",
            "title": "Agreement Started",
            "subtitle": getattr(agreement, 'customer_name', None) or agreement.customer,
            "color": "green"
        })

    # Get movements
    movements = frappe.get_all(
        "Movements",
        filters={
            "agreement_type": agreement_type,
            "agreement_no": agreement_no
        },
        fields=["name", "movement_type", "date", "status", "vehicle", "out_customer", "in_customer"],
        order_by="date asc"
    )

    for mov in movements:
        color = "blue"
        if "Delivery" in (mov.movement_type or ""):
            color = "purple"
        elif "Workshop" in (mov.movement_type or ""):
            color = "red"
        elif "Custody" in (mov.movement_type or ""):
            color = "yellow"
        elif "Recovery" in (mov.movement_type or ""):
            color = "orange"
        elif "Replacement" in (mov.movement_type or ""):
            color = "purple"

        timeline.append({
            "date": cstr(mov.date),
            "type": "movement",
            "title": mov.movement_type,
            "subtitle": mov.status,
            "link": f"/app/movements/{mov.name}",
            "ref": mov.name,
            "color": color
        })

    # Agreement end if applicable
    status_field = 'lease_status' if agreement_type == 'Lease Agreement' else 'agreement_status'
    status = getattr(agreement, status_field, None)
    end_statuses = ['Completed', 'Terminated', 'Cancelled', 'Closed']

    if status in end_statuses:
        end_date = agreement.end_date if hasattr(agreement, 'end_date') else agreement.modified
        timeline.append({
            "date": cstr(end_date)[:10] if end_date else cstr(agreement.modified)[:10],
            "type": "ended",
            "title": f"Agreement {status}",
            "subtitle": None,
            "color": "green" if status == "Completed" else "red"
        })

    # Sort by date
    timeline.sort(key=lambda x: x.get("date", ""))

    return timeline


@frappe.whitelist()
def create_movement_from_agreement(agreement_type, agreement_name, movement_type, date, notes=None):
    """Create a movement from an agreement (Rental Agreement or Lease Agreement)"""

    # Get agreement details
    agreement = frappe.get_doc(agreement_type, agreement_name)

    # Get vehicle and customer from agreement
    vehicle = agreement.vehicle
    customer = agreement.customer

    if not vehicle:
        frappe.throw(_("No vehicle found in the agreement"))

    # Create movement
    movement = frappe.get_doc({
        "doctype": "Movements",
        "movement_type": movement_type,
        "date": date,
        "vehicle": vehicle,
        "agreement_type": agreement_type,
        "agreement_no": agreement_name,
        "lease_agreement": agreement_name if agreement_type == "Lease Agreement" else None,
        "out_customer": customer,
        "out_date_time": now_datetime(),
        "out_notes": notes,
        "status": "Draft"
    })

    movement.insert()

    return {"name": movement.name, "success": True}


@frappe.whitelist()
def create_movement_from_customer(customer_name, vehicle, movement_type, date, notes=None):
    """Create a movement for a customer's vehicle"""

    # Validate vehicle belongs to customer (via active agreement)
    active_agreements = get_customer_active_vehicles(customer_name)
    vehicle_found = False
    agreement_info = None

    for ag in active_agreements:
        if ag.get("vehicle") == vehicle:
            vehicle_found = True
            agreement_info = ag
            break

    if not vehicle_found:
        frappe.throw(_("Vehicle {0} is not currently assigned to customer {1}").format(vehicle, customer_name))

    # Create movement
    movement = frappe.get_doc({
        "doctype": "Movements",
        "movement_type": movement_type,
        "date": date,
        "vehicle": vehicle,
        "agreement_type": agreement_info.get("agreement_type") if agreement_info else None,
        "agreement_no": agreement_info.get("agreement_name") if agreement_info else None,
        "lease_agreement": agreement_info.get("agreement_name") if agreement_info and agreement_info.get("agreement_type") == "Lease Agreement" else None,
        "out_customer": customer_name,
        "out_date_time": now_datetime(),
        "out_notes": notes,
        "status": "Draft"
    })

    movement.insert()

    return {"name": movement.name, "success": True}


@frappe.whitelist()
def process_vehicle_replacement(agreement_type, agreement_name, current_vehicle, replacement_vehicle,
                                 in_mileage, in_fuel_percentage, in_notes,
                                 out_mileage, out_fuel_percentage, out_notes, reason):
    """
    Process vehicle replacement with chronological flow:
    1. First create IN movement for current vehicle (Replacement - Customer Return)
    2. Then create OUT movement for replacement vehicle (Replacement - Vehicle Out)
    3. Update agreement with new vehicle
    """

    # Get agreement details
    agreement = frappe.get_doc(agreement_type, agreement_name)
    customer = agreement.customer

    # Validate vehicles are different
    if current_vehicle == replacement_vehicle:
        frappe.throw(_("Replacement vehicle must be different from current vehicle"))

    # Validate replacement vehicle is available
    replacement_vehicle_doc = frappe.get_doc("Vehicle", replacement_vehicle)
    if replacement_vehicle_doc.status != "Available":
        frappe.throw(_("Replacement vehicle {0} is not available (status: {1})").format(
            replacement_vehicle, replacement_vehicle_doc.status))

    current_time = now_datetime()

    # Step 1: Create IN movement for current vehicle (Customer Return)
    in_movement = frappe.get_doc({
        "doctype": "Movements",
        "movement_type": "Replacement - Customer Return",
        "date": getdate(),
        "vehicle": current_vehicle,
        "agreement_type": agreement_type,
        "agreement_no": agreement_name,
        "lease_agreement": agreement_name if agreement_type == "Lease Agreement" else None,
        "is_replacement": 1,
        "in_customer": customer,
        "in_date_time": current_time,
        "in_mileage": in_mileage,
        "in_fuel_percentage": in_fuel_percentage,
        "in_notes": in_notes + "\n\nReplacement Reason: " + reason if in_notes else "Replacement Reason: " + reason,
        "status": "Returned"
    })
    in_movement.insert()

    # Step 2: Create OUT movement for replacement vehicle
    # Add a small time offset to ensure chronological order
    from datetime import timedelta
    out_time = current_time + timedelta(seconds=1)

    out_movement = frappe.get_doc({
        "doctype": "Movements",
        "movement_type": "Replacement - Vehicle Out",
        "date": getdate(),
        "vehicle": replacement_vehicle,
        "replacement_vehicle": replacement_vehicle,
        "agreement_type": agreement_type,
        "agreement_no": agreement_name,
        "lease_agreement": agreement_name if agreement_type == "Lease Agreement" else None,
        "is_replacement": 1,
        "parent_movement": in_movement.name,
        "out_customer": customer,
        "out_date_time": out_time,
        "out_mileage": out_mileage,
        "out_fuel_percentage": out_fuel_percentage,
        "out_notes": out_notes + "\n\nReplaces: " + current_vehicle if out_notes else "Replaces: " + current_vehicle,
        "status": "Out Only"
    })
    out_movement.insert()

    # Step 3: Update vehicle statuses
    # Current vehicle becomes available
    frappe.db.set_value("Vehicle", current_vehicle, "status", "Available")

    # Replacement vehicle becomes rented/leased
    new_status = "Rented Out"  # Default for rental
    frappe.db.set_value("Vehicle", replacement_vehicle, "status", new_status)

    # Step 4: Update agreement with new vehicle
    frappe.db.set_value(agreement_type, agreement_name, "vehicle", replacement_vehicle)

    frappe.db.commit()

    return {
        "success": True,
        "in_movement": in_movement.name,
        "out_movement": out_movement.name,
        "message": _("Vehicle replacement completed. {0} returned, {1} issued.").format(
            current_vehicle, replacement_vehicle)
    }


@frappe.whitelist()
def get_customer_active_vehicles(customer_name):
    """Get all vehicles currently assigned to a customer via active agreements"""
    vehicles = []

    # Check Rental Agreements
    rental_agreements = frappe.get_all(
        "Rental Agreement",
        filters={"customer": customer_name, "agreement_status": "Active"},
        fields=["name", "vehicle", "customer"]
    )
    for ra in rental_agreements:
        vehicles.append({
            "vehicle": ra.vehicle,
            "agreement_type": "Rental Agreement",
            "agreement_name": ra.name
        })

    # Check Lease Agreements
    lease_agreements = frappe.get_all(
        "Lease Agreement",
        filters={"customer": customer_name, "lease_status": "Active"},
        fields=["name", "vehicle", "customer"]
    )
    for la in lease_agreements:
        vehicles.append({
            "vehicle": la.vehicle,
            "agreement_type": "Lease Agreement",
            "agreement_name": la.name
        })

    # Check Lease to Own
    lease_to_own = frappe.get_all(
        "Lease to Own",
        filters={"customer": customer_name, "status": "Active"},
        fields=["name", "vehicle", "customer"]
    )
    for lto in lease_to_own:
        vehicles.append({
            "vehicle": lto.vehicle,
            "agreement_type": "Lease to Own",
            "agreement_name": lto.name
        })

    return vehicles
