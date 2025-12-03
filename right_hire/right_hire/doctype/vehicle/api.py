# File: your_app/your_app/vehicles/api.py
# Server-side VIN decoder with auto-create for Vehicles Model

import frappe
import requests
from frappe import _

@frappe.whitelist()
def decode_vehicle_vin(vin, model_year=None):
    """
    Decode VIN using NHTSA vPIC API
    
    Args:
        vin (str): Vehicle Identification Number
        model_year (str, optional): Model year for better accuracy
    
    Returns:
        dict: Decoded vehicle information
    """
    if not vin:
        frappe.throw(_("VIN is required"))
    
    # Clean VIN
    vin = vin.strip().upper()
    
    # Validate VIN length
    if len(vin) < 11:
        frappe.throw(_("VIN must be at least 11 characters long"))
    
    # Check for invalid characters in full VIN
    if len(vin) == 17:
        invalid_chars = set('IOQ')
        if any(char in invalid_chars for char in vin):
            frappe.throw(_("VIN cannot contain letters I, O, or Q"))
    
    try:
        # Build API URL for RapidAPI car-api2
        api_url = f"https://car-api2.p.rapidapi.com/api/vin/{vin}"
        headers = {
            'x-rapidapi-host': 'car-api2.p.rapidapi.com',
            'x-rapidapi-key': '60d40f8d72msh2b2f2454f08ea4dp1e7250jsnafc12c2141f1'
        }

        # Make API request
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()

        if data:
            # Map to your DocType fields
            mapped_data = map_to_vehicle_fields(data)

            # Create manufacturer and model if they don't exist
            make_name = create_manufacturer_if_not_exists(data)
            model_name = create_vehicle_model_if_not_exists(data, make_name)

            # Add the linked fields to mapped data
            if make_name:
                mapped_data['make'] = make_name
                frappe.msgprint(_("Manufacturer set: {0}").format(make_name), indicator='blue', alert=True)

            if model_name:
                mapped_data['model'] = model_name
                frappe.msgprint(_("Model set: {0}").format(model_name), indicator='blue', alert=True)

            # Store complete JSON response
            import json
            mapped_data['vin_decode_data'] = json.dumps(data, indent=2)

            return {
                "success": True,
                "data": mapped_data,
                "raw_data": data,
                "message": _("VIN decoded successfully")
            }
        else:
            return {
                "success": False,
                "message": _("No data returned from API"),
                "data": None
            }
            
    except requests.exceptions.Timeout:
        frappe.log_error("VIN Decode Timeout", "VIN Decoder")
        return {
            "success": False,
            "message": _("Request timed out. Please try again."),
        }
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"VIN Decode Error: {str(e)}", "VIN Decoder")
        return {
            "success": False,
            "message": _("Failed to connect to VIN decoder service"),
            "error": str(e)
        }
    except Exception as e:
        frappe.log_error(f"VIN Decode Error: {str(e)}", "VIN Decoder")
        return {
            "success": False,
            "message": _("An error occurred while decoding VIN"),
            "error": str(e)
        }


def create_manufacturer_if_not_exists(api_data):
    """
    Create Vehicle Make record if it doesn't exist

    Args:
        api_data (dict): API response data

    Returns:
        str: Vehicle Make name
    """
    # Support both old NHTSA API and new RapidAPI format
    make = api_data.get("make") or api_data.get("Make")
    if not make or make == "Not Applicable":
        return None

    # Clean the make name
    make = make.strip()

    # Check if make exists
    existing_make = frappe.db.get_value("Vehicle Make",
        filters={"make_name": make},
        fieldname="name"
    )

    if existing_make:
        return existing_make

    try:
        # Double-check before creating (prevent race condition)
        existing_make = frappe.db.get_value("Vehicle Make",
            filters={"make_name": make},
            fieldname="name"
        )

        if existing_make:
            return existing_make

        # Create new make
        make_doc = frappe.get_doc({
            "doctype": "Vehicle Make",
            "make_name": make,
        })

        make_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        frappe.db.commit()

        frappe.msgprint(_("Created new make: {0}").format(make), alert=True)

        # Return the name of the created document
        return make_doc.name

    except frappe.DuplicateEntryError:
        # Make was created by another process, fetch and return it
        frappe.db.rollback()
        existing_make = frappe.db.get_value("Vehicle Make",
            filters={"make_name": make},
            fieldname="name"
        )
        return existing_make

    except Exception as e:
        frappe.log_error(f"Error creating make {make}: {str(e)}", "VIN Decoder")
        frappe.db.rollback()
        # Try to return existing make if any
        existing_make = frappe.db.get_value("Vehicle Make",
            filters={"make_name": make},
            fieldname="name"
        )
        return existing_make if existing_make else None


def create_vehicle_model_if_not_exists(api_data, make_name):
    """
    Create Vehicle Model record if it doesn't exist

    Args:
        api_data (dict): API response data
        make_name (str): Vehicle Make name

    Returns:
        str: Model name
    """
    # Support both old NHTSA API and new RapidAPI format
    model = api_data.get("model") or api_data.get("Model")
    if not model or model == "Not Applicable":
        return None

    # Clean the model name
    model = model.strip()

    # Check if model exists with this make
    existing_model = frappe.db.get_value("Vehicle Model",
        filters={"model_name": model, "make": make_name},
        fieldname="name"
    )

    if existing_model:
        return existing_model

    try:
        # Double-check before creating (prevent race condition)
        existing_model = frappe.db.get_value("Vehicle Model",
            filters={"model_name": model, "make": make_name},
            fieldname="name"
        )

        if existing_model:
            return existing_model

        # Create new vehicle model
        model_doc = frappe.get_doc({
            "doctype": "Vehicle Model",
            "model_name": model,
            "make": make_name,
        })

        model_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        frappe.db.commit()

        frappe.msgprint(_("Created new model: {0}").format(model), alert=True)

        # Return the name of the created document
        return model_doc.name

    except frappe.DuplicateEntryError:
        # Model was created by another process, fetch and return it
        frappe.db.rollback()
        existing_model = frappe.db.get_value("Vehicle Model",
            filters={"model_name": model, "make": make_name},
            fieldname="name"
        )
        return existing_model

    except Exception as e:
        frappe.log_error(f"Error creating vehicle model {model}: {str(e)}", "VIN Decoder")
        frappe.db.rollback()
        # Try to return existing model if any
        existing_model = frappe.db.get_value("Vehicle Model",
            filters={"model_name": model, "make": make_name},
            fieldname="name"
        )
        return existing_model if existing_model else None


def map_to_vehicle_fields(api_data):
    """Map API response to Vehicle DocType fields"""

    # Helper function to get value safely from specs
    def get_spec_value(key):
        specs = api_data.get('specs', {})
        val = specs.get(key)
        if val and val not in ["Not Applicable", "null", "", None]:
            return val
        return None

    # Helper function to get value from root
    def get_value(key):
        val = api_data.get(key)
        if val and val not in ["Not Applicable", "null", "", None]:
            return val
        return None

    # Map fuel type
    def map_fuel_type(api_fuel):
        if not api_fuel:
            return None

        fuel_map = {
            'Gasoline': 'Petrol',
            'Diesel': 'Diesel',
            'Electric': 'Electric',
            'Hybrid': 'Hybrid',
            'Plug-in Hybrid': 'Hybrid',
        }

        for key, value in fuel_map.items():
            if key.lower() in api_fuel.lower():
                return value
        return None

    # Map transmission
    def map_transmission(api_trans):
        if not api_trans:
            return None

        api_trans_lower = api_trans.lower()
        if 'manual' in api_trans_lower:
            return 'Manual'
        elif 'cvt' in api_trans_lower:
            return 'CVT'
        elif 'dct' in api_trans_lower:
            return 'DCT'
        elif 'auto' in api_trans_lower:
            return 'Automatic'
        return None

    # Map body type
    def map_body_type(api_body):
        if not api_body:
            return None

        body_map = {
            'Sedan': 'Sedan',
            'SUV': 'SUV',
            'Pickup': 'Pickup',
            'Truck': 'Truck',
            'Van': 'Van',
            'Coupe': 'Coupe',
            'Convertible': 'Convertible',
            'Wagon': 'Wagon',
            'Hatchback': 'Hatchback',
        }

        for key, value in body_map.items():
            if key.lower() in api_body.lower():
                return value
        return None

    # Build mapped data
    mapped = {
        'year': get_value('year'),
        'variant': get_value('trim'),
        'transmission': map_transmission(get_spec_value('transmission_style')),
        'fuel_type': map_fuel_type(get_spec_value('fuel_type_primary')),
        'seating_capacity': int(get_spec_value('number_of_seats')) if get_spec_value('number_of_seats') else None,
        'body_type': map_body_type(get_spec_value('body_class')),
        'engine_capacity': get_spec_value('displacement_l'),
    }

    # Remove None values
    mapped = {k: v for k, v in mapped.items() if v is not None}

    return mapped


@frappe.whitelist()
def auto_fill_vehicle(doc_name, vin, model_year=None):
    """
    Auto-fill Vehicle document from VIN
    
    Args:
        doc_name (str): Name of Vehicles document
        vin (str): VIN
        model_year (str, optional): Model year
    
    Returns:
        dict: Result
    """
    # Decode VIN
    result = decode_vehicle_vin(vin, model_year)
    
    if not result.get("success"):
        return result
    
    # Get document
    try:
        doc = frappe.get_doc("Vehicles", doc_name)
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": _("Vehicle document not found")
        }
    
    # Update fields
    mapped_data = result.get("data", {})
    
    for field, value in mapped_data.items():
        if field.startswith('_'):  # Skip internal fields
            continue
        
        if hasattr(doc, field):
            setattr(doc, field, value)
    
    # Save
    doc.save()
    
    return {
        "success": True,
        "message": _("Vehicle updated successfully"),
        "data": mapped_data
    }


@frappe.whitelist()
def validate_vin(vin):
    """
    Validate VIN format
    
    Args:
        vin (str): VIN to validate
    
    Returns:
        dict: Validation result
    """
    if not vin:
        return {"valid": False, "message": "VIN is empty"}
    
    vin = vin.strip().upper()
    
    # Check length
    if len(vin) < 11:
        return {"valid": False, "message": "VIN must be at least 11 characters"}
    
    # Check for invalid characters in full VIN
    if len(vin) == 17:
        invalid_chars = set('IOQ')
        found_invalid = [c for c in vin if c in invalid_chars]
        if found_invalid:
            return {
                "valid": False,
                "message": f"VIN cannot contain letters: {', '.join(found_invalid)}"
            }
    
    return {"valid": True, "message": "VIN is valid"}


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

            # Check if make exists
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
                    frappe.log_error(f"Error creating make {make_name}: {str(e)}", "Make Sync")

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
        frappe.log_error(f"Make Sync Error: {str(e)}", "Make Sync")
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
                    frappe.log_error(f"Error creating make {make_name}: {str(e)}", "Model Sync")
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
                    frappe.log_error(f"Error creating model {model_name}: {str(e)}", "Model Sync")
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
        frappe.log_error(f"Model Sync Error: {str(e)}", "Model Sync")
        return {
            "success": False,
            "message": _("Failed to sync models: {0}").format(str(e))
        }
