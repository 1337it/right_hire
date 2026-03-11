# Debug helper functions
import frappe

def check_rta_synced_vehicles():
    """Check vehicles with RTA data"""
    vehicles = frappe.db.sql("""
        SELECT name, plate_no, rta_vehicle_id, rta_registration_front,
               rta_registration_back, rta_last_sync
        FROM tabVehicle
        WHERE rta_vehicle_id IS NOT NULL AND rta_vehicle_id != ''
        LIMIT 10
    """, as_dict=True)

    result = []
    for v in vehicles:
        result.append({
            "name": v.name,
            "plate_no": v.plate_no,
            "rta_vehicle_id": v.rta_vehicle_id,
            "front_image": "Yes" if v.rta_registration_front else "No",
            "back_image": "Yes" if v.rta_registration_back else "No",
            "last_sync": str(v.rta_last_sync) if v.rta_last_sync else "Never"
        })

    return result
