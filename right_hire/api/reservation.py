import frappe
from frappe import _

@frappe.whitelist()
def create_reservation(customer, pickup_datetime, return_datetime, rate_plan, 
                       branch, vehicle=None, driver=None, extras=None):
    """Create a new reservation"""
    try:
        reservation = frappe.get_doc({
            "doctype": "Reservation",
            "customer": customer,
            "driver": driver,
            "pickup_datetime": pickup_datetime,
            "return_datetime": return_datetime,
            "rate_plan": rate_plan,
            "branch": branch,
            "vehicle": vehicle,
            "reservation_status": "Draft"
        })
        
        if extras:
            import json
            extras_list = json.loads(extras) if isinstance(extras, str) else extras
            for extra in extras_list:
                reservation.append("extras", extra)
        
        reservation.insert()
        return {"success": True, "reservation": reservation.name}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Reservation Failed")
        return {"error": str(e)}
