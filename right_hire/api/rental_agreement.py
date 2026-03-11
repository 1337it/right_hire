import frappe
from frappe import _

@frappe.whitelist()
def start_rental(agreement, odometer_out, fuel_out):
    """Start a rental agreement"""
    try:
        doc = frappe.get_doc("Rental Agreement", agreement)
        doc.odometer_out = odometer_out
        doc.fuel_out = fuel_out
        doc.start_rental()
        return {"success": True, "message": "Rental started successfully"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Start Rental Failed")
        return {"error": str(e)}

@frappe.whitelist()
def return_vehicle(agreement, odometer_in, fuel_in):
    """Process vehicle return"""
    try:
        doc = frappe.get_doc("Rental Agreement", agreement)
        doc.odometer_in = odometer_in
        doc.fuel_in = fuel_in
        doc.return_vehicle()
        return {"success": True, "outstanding": doc.outstanding_amount}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Return Vehicle Failed")
        return {"error": str(e)}

@frappe.whitelist()
def add_charge(agreement, charge_type, description, amount):
    """Add a charge to rental agreement"""
    try:
        doc = frappe.get_doc("Rental Agreement", agreement)
        doc.append("charges", {
            "charge_type": charge_type,
            "description": description,
            "qty": 1,
            "rate": amount,
            "amount": amount
        })
        doc.save()
        return {"success": True, "message": "Charge added successfully"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Add Charge Failed")
        return {"error": str(e)}

@frappe.whitelist()
def close_agreement(agreement):
    """Close a rental agreement"""
    try:
        doc = frappe.get_doc("Rental Agreement", agreement)
        doc.agreement_status = "Closed"
        doc.save()
        return {"success": True, "message": "Agreement closed successfully"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Close Agreement Failed")
        return {"error": str(e)}
