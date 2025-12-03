import frappe
from frappe import _

@frappe.whitelist()
def check_availability(vehicle, start_datetime, end_datetime):
    """Check if a vehicle is available for booking"""
    try:
        vehicle_doc = frappe.get_doc("Vehicle", vehicle)
        is_available = vehicle_doc.check_availability(start_datetime, end_datetime)
        return {
            "available": is_available,
            "vehicle": vehicle,
            "current_status": vehicle_doc.status
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Vehicle Availability Check Failed")
        return {"error": str(e)}

@frappe.whitelist()
def search_available_vehicles(start_datetime, end_datetime, branch=None, make=None, model=None):
    """Search for available vehicles"""
    filters = {"status": "Available", "availability_status": 1}
    if branch:
        filters["branch"] = branch
    if make:
        filters["make"] = make
    if model:
        filters["model"] = model
    
    vehicles = frappe.get_all("Vehicle", filters=filters,
        fields=["name", "make", "model", "year", "plate_no", "color", "transmission", "fuel_type"])
    
    available = []
    for vehicle in vehicles:
        vehicle_doc = frappe.get_doc("Vehicle", vehicle.name)
        if vehicle_doc.check_availability(start_datetime, end_datetime):
            available.append(vehicle)
    
    return available
