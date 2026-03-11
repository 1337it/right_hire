import frappe
from frappe import _
from frappe.utils import getdate, cstr, today
import io
import csv


def _get_customer_for_user():
    """Resolve the current session user to a Right Hire Customer record."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please log in to access the portal"), frappe.AuthenticationError)

    customer = frappe.db.get_value(
        "Customer",  # db.get_value skips permissions
        {"email": user},
        ["name", "customer_name", "account_id"],
        as_dict=True,
    )
    if not customer:
        frappe.throw(_("No customer account found for this user"), frappe.PermissionError)
    return customer


def _get_active_leases(customer_name):
    """Return active/draft Lease Agreements for the given customer."""
    return frappe.get_all(
        "Lease Agreement",
        ignore_permissions=True,
        filters={
            "customer": customer_name,
            "lease_status": ["in", ["Active", "Draft"]],
            "docstatus": ["!=", 2],
        },
        fields=[
            "name", "vehicle", "start_date", "end_date", "lease_status",
            "plate_no", "vehicle_details", "vehicle_color", "vehicle_year",
        ],
        order_by="start_date desc",
    )


def _validate_vehicle_access(customer_name, vehicle):
    """Ensure the customer has an active lease for the given vehicle.

    Returns the lease doc dict with start_date/end_date so callers can clamp
    date ranges.
    """
    lease = frappe.db.get_value(
        "Lease Agreement",  # ignore_permissions via db.get_value (no perm check)
        {
            "customer": customer_name,
            "vehicle": vehicle,
            "lease_status": ["in", ["Active", "Draft"]],
            "docstatus": ["!=", 2],
        },
        ["name", "start_date", "end_date"],
        as_dict=True,
    )
    if not lease:
        frappe.throw(_("You do not have access to this vehicle"), frappe.PermissionError)
    return lease


def _clamp_dates(from_date, to_date, lease):
    """Clamp requested date range to the lease period."""
    lease_start = getdate(lease.start_date)
    lease_end = getdate(lease.end_date) if lease.end_date else getdate("2099-12-31")

    fd = max(getdate(from_date), lease_start) if from_date else lease_start
    td = min(getdate(to_date), lease_end) if to_date else lease_end
    return fd, td


def _parse_vehicles(vehicle):
    """Parse a comma-separated vehicle string into a list of vehicle IDs."""
    if not vehicle:
        frappe.throw(_("No vehicle specified"), frappe.ValidationError)
    return [v.strip() for v in vehicle.split(",") if v.strip()]


def _get_vehicle_plate(vehicle):
    """Return the plate_no for a vehicle (used to identify rows in multi-vehicle results)."""
    return frappe.db.get_value("Vehicle", vehicle, "plate_no") or vehicle


# ──────────────────────────────────────────────────────────────
# Public API endpoints
# ──────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_customer_vehicles():
    """Return vehicles from active lease agreements for the logged-in customer."""
    customer = _get_customer_for_user()
    leases = _get_active_leases(customer.name)

    vehicles = []
    for la in leases:
        if not la.vehicle:
            continue

        veh = frappe.db.get_value(
            "Vehicle",  # db.get_value skips permissions
            la.vehicle,
            ["name", "plate_code", "plate_no", "make", "model", "year", "color"],
            as_dict=True,
        )
        if not veh:
            continue

        vehicles.append({
            "vehicle": veh.name,
            "plate_code": veh.plate_code,
            "plate_no": veh.plate_no,
            "make": veh.make,
            "model": veh.model,
            "year": veh.year,
            "color": veh.color,
            "lease_start": cstr(la.start_date),
            "lease_end": cstr(la.end_date) if la.end_date else None,
            "lease_status": la.lease_status,
            "lease_name": la.name,
        })

    return vehicles


@frappe.whitelist()
def get_vehicle_salik(vehicle, from_date=None, to_date=None):
    """Return Salik transactions for one or more vehicles within the (clamped) date range.

    vehicle can be a single vehicle ID or comma-separated list.
    """
    customer = _get_customer_for_user()
    vehicles = _parse_vehicles(vehicle)
    all_data = []

    for veh in vehicles:
        lease = _validate_vehicle_access(customer.name, veh)
        fd, td = _clamp_dates(from_date, to_date, lease)

        rows = frappe.get_all(
            "Salik Transaction",
            ignore_permissions=True,
            filters={
                "vehicle": veh,
                "transaction_date": ["between", [fd, td]],
                "charge_type": ["!=", "Non-Revenue"],
            },
            fields=[
                "name", "transaction_date", "transaction_time",
                "gate_location", "direction", "toll_amount",
                "toll_schedule",
            ],
            order_by="transaction_date desc, transaction_time desc",
        )

        plate_no = _get_vehicle_plate(veh)
        for r in rows:
            r["plate_no"] = plate_no
        all_data.extend(rows)

    all_data.sort(key=lambda r: (cstr(r.get("transaction_date", "")), cstr(r.get("transaction_time", ""))), reverse=True)
    total_amount = sum(r.toll_amount or 0 for r in all_data)

    return {
        "data": all_data,
        "total_count": len(all_data),
        "total_amount": total_amount,
        "from_date": cstr(from_date) if from_date else "",
        "to_date": cstr(to_date) if to_date else "",
        "multi_vehicle": len(vehicles) > 1,
    }


@frappe.whitelist()
def get_vehicle_darb(vehicle, from_date=None, to_date=None):
    """Return Darb transactions for one or more vehicles within the (clamped) date range.

    vehicle can be a single vehicle ID or comma-separated list.
    """
    customer = _get_customer_for_user()
    vehicles = _parse_vehicles(vehicle)
    all_data = []

    for veh in vehicles:
        lease = _validate_vehicle_access(customer.name, veh)
        fd, td = _clamp_dates(from_date, to_date, lease)

        rows = frappe.get_all(
            "Darb Transaction",
            ignore_permissions=True,
            filters={
                "vehicle": veh,
                "transaction_date": ["between", [fd, td]],
            },
            fields=[
                "name", "transaction_date", "transaction_time",
                "gate_location", "direction", "toll_amount",
            ],
            order_by="transaction_date desc, transaction_time desc",
        )

        plate_no = _get_vehicle_plate(veh)
        for r in rows:
            r["plate_no"] = plate_no
        all_data.extend(rows)

    all_data.sort(key=lambda r: (cstr(r.get("transaction_date", "")), cstr(r.get("transaction_time", ""))), reverse=True)
    total_amount = sum(r.toll_amount or 0 for r in all_data)

    return {
        "data": all_data,
        "total_count": len(all_data),
        "total_amount": total_amount,
        "from_date": cstr(from_date) if from_date else "",
        "to_date": cstr(to_date) if to_date else "",
        "multi_vehicle": len(vehicles) > 1,
    }


def _parse_fine_date(date_str):
    """Parse fine_date which is a Data field stored in various formats:
    'dd/mm/yyyy', 'dd Mon YYYY', or 'YYYY-MM-DD'. Returns a date object or None."""
    if not date_str:
        return None
    from datetime import datetime
    # Try dd/mm/yyyy format first (most common from RTA)
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except Exception:
        pass
    # Try YYYY-MM-DD format
    try:
        return getdate(date_str)
    except Exception:
        pass
    # Try "02 May 2025" format
    try:
        return datetime.strptime(date_str.strip(), "%d %b %Y").date()
    except Exception:
        return None


@frappe.whitelist()
def get_vehicle_fines(vehicle, from_date=None, to_date=None):
    """Return Traffic Fines for one or more vehicles within the (clamped) date range.

    vehicle can be a single vehicle ID or comma-separated list.
    fine_date is a Data (varchar) field, not a Date field, so we cannot use
    SQL date comparisons.  Fetch all fines for the vehicle and filter in Python.
    """
    customer = _get_customer_for_user()
    vehicles = _parse_vehicles(vehicle)
    all_data = []

    for veh in vehicles:
        lease = _validate_vehicle_access(customer.name, veh)
        fd, td = _clamp_dates(from_date, to_date, lease)

        all_fines = frappe.get_all(
            "Traffic Fine",
            ignore_permissions=True,
            filters={"vehicle": veh, "paid": 0},
            fields=[
                "name", "fine_date", "fine_time", "fine_number",
                "location", "source", "details",
                "amount", "black_points", "ticket_photo",
            ],
        )

        plate_no = _get_vehicle_plate(veh)
        for row in all_fines:
            parsed = _parse_fine_date(row.fine_date)
            if parsed and fd <= parsed <= td:
                row["_sort_date"] = parsed
                row["fine_date"] = str(parsed)
                row["plate_no"] = plate_no
                row["has_photo"] = 1 if row.get("ticket_photo") else 0
                row.pop("ticket_photo", None)
                all_data.append(row)

    all_data.sort(key=lambda r: (r.pop("_sort_date"), r.get("fine_time") or ""), reverse=True)
    total_amount = sum(r.amount or 0 for r in all_data)

    return {
        "data": all_data,
        "total_count": len(all_data),
        "total_amount": total_amount,
        "from_date": cstr(from_date) if from_date else "",
        "to_date": cstr(to_date) if to_date else "",
        "multi_vehicle": len(vehicles) > 1,
    }


@frappe.whitelist()
def get_ticket_photo(fine_name):
    """Return the ticket photo as base64 data URI for a traffic fine (with access validation)."""
    import base64

    customer = _get_customer_for_user()

    # Get the fine and validate the customer has access to the vehicle
    fine = frappe.db.get_value(
        "Traffic Fine", fine_name,
        ["vehicle", "ticket_photo"], as_dict=True
    )
    if not fine:
        frappe.throw(_("Fine not found"), frappe.DoesNotExistError)

    _validate_vehicle_access(customer.name, fine.vehicle)

    if not fine.ticket_photo:
        return {"photo_url": None}

    # Read the private file and return as base64 data URI
    try:
        file_doc = frappe.get_doc("File", {"file_url": fine.ticket_photo})
        content = file_doc.get_content()

        ext = fine.ticket_photo.rsplit(".", 1)[-1].lower()
        mime = "image/png" if ext == "png" else "image/jpeg"

        b64 = base64.b64encode(content).decode("utf-8")
        return {"photo_url": f"data:{mime};base64,{b64}"}
    except Exception:
        return {"photo_url": None}


EXPORT_COLUMNS = {
    "salik": [
        ("transaction_date", "Date"),
        ("transaction_time", "Time"),
        ("gate_location", "Location"),
        ("direction", "Direction"),
        ("toll_schedule", "Schedule"),
        ("toll_amount", "Amount (AED)"),
    ],
    "darb": [
        ("transaction_date", "Date"),
        ("transaction_time", "Time"),
        ("gate_location", "Location"),
        ("direction", "Direction"),
        ("toll_amount", "Amount (AED)"),
    ],
    "fines": [
        ("fine_date", "Date"),
        ("fine_time", "Time"),
        ("fine_number", "Fine #"),
        ("location", "Location"),
        ("details", "Violation"),
        ("amount", "Amount (AED)"),
        ("black_points", "Points"),
    ],
}

# Vehicle column prepended when exporting multi-vehicle data
VEHICLE_COLUMN = ("plate_no", "Vehicle")


@frappe.whitelist()
def export_data(vehicle, tab, from_date=None, to_date=None, fmt="csv"):
    """Export Salik/Darb/Fines data as CSV or PDF."""
    tab_map = {
        "salik": get_vehicle_salik,
        "darb": get_vehicle_darb,
        "fines": get_vehicle_fines,
    }
    fn = tab_map.get(tab)
    if not fn:
        frappe.throw(_("Invalid tab: {0}").format(tab))

    columns = list(EXPORT_COLUMNS.get(tab, []))
    result = fn(vehicle, from_date, to_date)
    rows = result["data"]

    # Prepend vehicle column when multiple vehicles selected
    if result.get("multi_vehicle"):
        columns = [VEHICLE_COLUMN] + columns

    if fmt == "csv":
        return _build_csv(rows, columns, tab)
    elif fmt == "pdf":
        return _build_pdf(rows, columns, tab, vehicle, result)
    else:
        frappe.throw(_("Unsupported format: {0}").format(fmt))


def _build_csv(rows, columns, tab):
    """Return CSV content as a string for download."""
    if not rows:
        return ""

    output = io.StringIO()
    keys = [c[0] for c in columns]
    labels = [c[1] for c in columns]

    writer = csv.writer(output)
    writer.writerow(labels)
    for row in rows:
        writer.writerow([cstr(row.get(k, "")) for k in keys])

    csv_content = output.getvalue()

    frappe.response["type"] = "download"
    frappe.response["filename"] = f"{tab}_export.csv"
    frappe.response["filecontent"] = csv_content

    return csv_content


def _get_letterhead_html():
    """Fetch the default Letter Head header and footer HTML."""
    lh_name = frappe.db.get_value("Letter Head", {"is_default": 1}, "name")
    if not lh_name:
        return "", ""
    lh = frappe.get_doc("Letter Head", lh_name)
    header = lh.content or ""
    footer = getattr(lh, "footer", "") or ""
    return header, footer


def _build_pdf(rows, columns, tab, vehicle, result):
    """Generate a PDF from an HTML table with letterhead and return it for download."""
    from frappe.utils.pdf import get_pdf

    tab_title = tab.replace("_", " ").title()
    keys = [c[0] for c in columns]
    labels = [c[1] for c in columns]

    lh_header, lh_footer = _get_letterhead_html()

    header_html = "".join(
        f"<th style='padding:6px 10px;border:1px solid #ccc;background:#f5f5f5;text-align:left;font-size:11px;'>{lbl}</th>"
        for lbl in labels
    )

    table_rows = ""
    for row in rows:
        cells = "".join(
            f"<td style='padding:5px 10px;border:1px solid #eee;font-size:11px;'>{cstr(row.get(k, ''))}</td>"
            for k in keys
        )
        table_rows += f"<tr>{cells}</tr>"

    if not rows:
        table_rows = f"<tr><td colspan='{len(columns)}' style='padding:20px;text-align:center;color:#999;'>No records found</td></tr>"

    html = f"""
    <html>
    <head><style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; }}
        .letterhead-header {{ text-align: center; margin-bottom: 10px; }}
        .letterhead-header img {{ max-width: 100%; height: auto; }}
        .letterhead-footer {{ text-align: center; margin-top: 20px; }}
        .letterhead-footer img {{ max-width: 100%; height: auto; }}
        .report-content {{ padding: 0 20px; }}
        h2 {{ color: #333; margin: 10px 0 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
        .summary {{ margin-top: 5px; font-size: 12px; color: #555; }}
    </style></head>
    <body>
        <div class="letterhead-header">{lh_header}</div>
        <div class="report-content">
            <h2>{tab_title} Report — {vehicle.replace(",", ", ")}</h2>
            <p class="summary">
                Period: {result.get('from_date', '')} to {result.get('to_date', '')} |
                Total records: {result.get('total_count', 0)} |
                Total amount: AED {result.get('total_amount', 0):,.2f}
            </p>
            <table>
                <thead><tr>{header_html}</tr></thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        <div class="letterhead-footer">{lh_footer}</div>
    </body>
    </html>
    """

    pdf_content = get_pdf(html)

    frappe.response["type"] = "download"
    frappe.response["filename"] = f"{tab}_report.pdf"
    frappe.response["filecontent"] = pdf_content

    return pdf_content
