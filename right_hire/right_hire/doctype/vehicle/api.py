# File: right_hire/right_hire/doctype/vehicle/api.py
# Vehicle API utilities - Make/Model sync

import frappe
import requests
from frappe import _


@frappe.whitelist()
def sync_makes_from_api():
    """
    Sync all vehicle makes from RapidAPI

    Returns:
        dict: Sync result with count of created/updated makes
    """
    api_url = "https://car-api2.p.rapidapi.com/api/makes?direction=asc&sort=id"
    headers = {
        'x-rapidapi-host': 'car-api2.p.rapidapi.com',
        'x-rapidapi-key': '60d40f8d72msh2b2f2454f08ea4dp1e7250jsnafc12c2141f1'
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("data"):
            return {
                "success": False,
                "message": _("No makes found in API response")
            }

        makes = data["data"]
        created = 0
        updated = 0

        for make_data in makes:
            make_name = make_data.get("name")
            api_id = make_data.get("id")

            if not make_name:
                continue

            # Check if make already exists
            existing = frappe.db.get_value("Vehicle Make",
                filters={"make_name": make_name},
                fieldname=["name", "api_id"],
                as_dict=True
            )

            if existing:
                # Update API ID if different
                if existing.api_id != api_id:
                    frappe.db.set_value("Vehicle Make", existing.name, "api_id", api_id)
                    updated += 1
            else:
                # Create new make
                try:
                    make_doc = frappe.get_doc({
                        "doctype": "Vehicle Make",
                        "make_name": make_name,
                        "api_id": api_id
                    })
                    make_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    created += 1
                except Exception as e:
                    frappe.log_error(title="Make Sync", message=f"Error creating make {make_name}: {str(e)}")
                    continue

        frappe.db.commit()

        return {
            "success": True,
            "message": _("Synced {0} makes ({1} created, {2} updated)").format(
                len(makes), created, updated
            ),
            "created": created,
            "updated": updated,
            "total": len(makes)
        }

    except Exception as e:
        frappe.log_error(title="Make Sync", message=f"Make Sync Error: {str(e)}")
        return {
            "success": False,
            "message": _("Failed to sync makes: {0}").format(str(e))
        }


@frappe.whitelist()
def sync_models_from_api(year=None, make_id=None):
    """
    Sync vehicle models from RapidAPI

    Args:
        year (int, optional): Filter by year
        make_id (int, optional): Filter by make ID

    Returns:
        dict: Sync result with count of created/updated models
    """
    # Build API URL
    api_url = "https://car-api2.p.rapidapi.com/api/models?sort=id&direction=asc&verbose=yes"

    if year:
        api_url += f"&year={year}"
    if make_id:
        api_url += f"&make_id={make_id}"

    headers = {
        'x-rapidapi-host': 'car-api2.p.rapidapi.com',
        'x-rapidapi-key': '60d40f8d72msh2b2f2454f08ea4dp1e7250jsnafc12c2141f1'
    }

    try:
        # Fetch all pages
        all_models = []
        page = 1
        total_pages = 1

        while page <= total_pages:
            url = f"{api_url}&page={page}"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("data"):
                all_models.extend(data["data"])

            # Get total pages from first request
            if page == 1 and data.get("collection"):
                total_pages = data["collection"].get("pages", 1)

            page += 1

            # Safety limit to avoid too many requests
            if page > 100:
                break

        if not all_models:
            return {
                "success": False,
                "message": _("No models found in API response")
            }

        created = 0
        updated = 0
        skipped = 0

        for model_data in all_models:
            model_name = model_data.get("name")
            api_id = model_data.get("id")
            make_api_id = model_data.get("make_id")
            make_info = model_data.get("make", {})
            make_name = make_info.get("name")

            if not model_name or not make_name:
                skipped += 1
                continue

            # Find or create the make first
            make_doc_name = frappe.db.get_value("Vehicle Make",
                filters={"make_name": make_name},
                fieldname="name"
            )

            if not make_doc_name:
                # Create the make if it doesn't exist
                try:
                    make_doc = frappe.get_doc({
                        "doctype": "Vehicle Make",
                        "make_name": make_name,
                        "api_id": make_api_id
                    })
                    make_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    make_doc_name = make_doc.name
                except Exception as e:
                    frappe.log_error(title="Model Sync", message=f"Error creating make {make_name}: {str(e)}")
                    skipped += 1
                    continue

            # Check if model exists
            existing = frappe.db.get_value("Vehicle Model",
                filters={"model_name": model_name, "make": make_doc_name},
                fieldname=["name", "api_id"],
                as_dict=True
            )

            if existing:
                # Update API ID if different
                if existing.api_id != api_id:
                    frappe.db.set_value("Vehicle Model", existing.name, "api_id", api_id)
                    updated += 1
            else:
                # Create new model
                try:
                    model_doc = frappe.get_doc({
                        "doctype": "Vehicle Model",
                        "model_name": model_name,
                        "make": make_doc_name,
                        "api_id": api_id
                    })
                    model_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    created += 1
                except Exception as e:
                    frappe.log_error(title="Model Sync", message=f"Error creating model {model_name}: {str(e)}")
                    skipped += 1

        frappe.db.commit()

        return {
            "success": True,
            "message": _("Synced {0} models ({1} created, {2} updated, {3} skipped)").format(
                len(all_models), created, updated, skipped
            ),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "total": len(all_models)
        }

    except Exception as e:
        frappe.log_error(title="Model Sync", message=f"Model Sync Error: {str(e)}")
        return {
            "success": False,
            "message": _("Failed to sync models: {0}").format(str(e))
        }
