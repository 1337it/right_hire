"""
Darb Integration Module
Fetches Darb toll transactions from the Darb API and saves them to Darb Transaction DocType

Available API endpoints:
  - GET /api/darb/transactions       - Summary with recent transactions
  - GET /api/darb/transactions/all   - All transactions (paginated, limit/offset)
  - GET /api/darb/transactions/range?start=DD/MM/YYYY&end=DD/MM/YYYY - By date range
"""

import frappe
import requests
import json
from datetime import datetime


DARB_API_BASE = "http://139.185.53.79:8001/api/darb/transactions"


def _parse_plate_info(plate_string):
	"""Parse plate string like 'FF DUBAI PRIVATE 49962' into components."""
	if not plate_string:
		return {}

	parts = plate_string.strip().split()
	if len(parts) >= 4:
		# Format: "CODE EMIRATE CATEGORY NUMBER"
		return {
			"plate_code": parts[0],
			"emirate": parts[1],
			"category": parts[2],
			"plate_no": parts[3],
		}
	elif len(parts) >= 2:
		return {
			"plate_code": parts[0],
			"plate_no": parts[-1],
		}
	return {"plate_no": plate_string}


def _find_vehicle_by_plate(plate_info):
	"""Find a Vehicle record matching the plate info from the API."""
	plate_no = plate_info.get("plate_no")
	if not plate_no:
		return None

	# Try exact plate_no match first
	vehicles = frappe.get_all(
		"Vehicle",
		filters={"plate_no": plate_no},
		fields=["name"]
	)
	if vehicles:
		return vehicles[0].name

	# Try partial match
	vehicles = frappe.get_all(
		"Vehicle",
		filters=[["plate_no", "like", f"%{plate_no}%"]],
		fields=["name"]
	)
	if vehicles:
		return vehicles[0].name

	return None


def _parse_date(date_str):
	"""Parse date from 'dd/mm/yyyy' or 'yyyy-mm-dd' format to date object."""
	if not date_str:
		return None
	for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
		try:
			return datetime.strptime(date_str.strip(), fmt).date()
		except Exception:
			continue
	return None


@frappe.whitelist()
def sync_darb_data():
	"""
	Fetch all Darb transactions from the API and save new ones.
	Called hourly via scheduler (5 AM - 6 PM).
	"""
	try:
		frappe.logger().info("Starting Darb transaction sync")

		# Get or create API Status record
		api_status_name = "Darb Tolls"
		if not frappe.db.exists("API Status", api_status_name):
			api_status = frappe.new_doc("API Status")
			api_status.api_name = api_status_name
			api_status.api_type = "Darb Tolls"
			api_status.enabled = 1
			api_status.insert(ignore_permissions=True)
		else:
			api_status = frappe.get_doc("API Status", api_status_name)

		frappe.db.set_value("API Status", api_status_name, {
			"status": "Running",
			"last_sync_time": datetime.now(),
		})

		# Fetch all transactions (paginated)
		all_transactions = []
		offset = 0
		limit = 1000

		while True:
			url = f"{DARB_API_BASE}/all?limit={limit}&offset={offset}"
			response = requests.get(url, timeout=60)
			response.raise_for_status()
			result = response.json()

			if not result.get("success"):
				break

			batch = result.get("data", [])
			all_transactions.extend(batch)

			# Check if there are more pages
			if len(batch) < limit:
				break
			offset += limit

		if not all_transactions:
			_update_darb_status("Success", records_fetched=0)
			frappe.logger().info("Darb sync: no transactions found")
			return {"status": "success", "new_transactions": 0, "message": "No transactions found"}

		new_count = _save_darb_transactions(all_transactions)

		_update_darb_status("Success", records_fetched=new_count)

		frappe.logger().info(f"Darb sync complete: {new_count} new from {len(all_transactions)} total")

		return {
			"status": "success",
			"total_from_api": len(all_transactions),
			"new_transactions": new_count,
		}

	except requests.exceptions.RequestException as e:
		error_msg = f"Darb API request failed: {str(e)[:200]}"
		frappe.log_error(title="Darb Integration", message=error_msg)
		_update_darb_status("Failed", error_message=error_msg)
		return {"status": "error", "message": error_msg}

	except Exception as e:
		error_msg = f"Darb sync error: {str(e)[:200]}"
		frappe.log_error(title="Darb Integration", message=error_msg)
		_update_darb_status("Failed", error_message=error_msg)
		return {"status": "error", "message": error_msg}


def _update_darb_status(status, records_fetched=0, error_message=None):
	"""Re-fetch and update the Darb API Status record to avoid stale doc issues."""
	try:
		if error_message and len(error_message) > 140:
			error_message = error_message[:140]
		if frappe.db.exists("API Status", "Darb Tolls"):
			doc = frappe.get_doc("API Status", "Darb Tolls")
			doc.update_status(status, records_fetched=records_fetched, error_message=error_message)
	except Exception as e:
		# Last resort: direct DB update
		try:
			frappe.db.set_value("API Status", "Darb Tolls", "status", status)
			frappe.db.commit()
		except Exception:
			pass


def _save_darb_transactions(transactions):
	"""Save Darb transactions to the Darb Transaction DocType."""
	new_count = 0

	for txn in transactions:
		try:
			plate_string = txn.get("plateNumber", "")
			plate_info = _parse_plate_info(plate_string)
			txn_date = _parse_date(txn.get("date"))
			txn_time = txn.get("time", "")
			toll_gate = txn.get("tollGate", "")
			amount = float(txn.get("amount", 0))

			if not txn_date:
				frappe.logger().warning(f"Skipping Darb txn with unparsable date: {txn.get('date')}")
				continue

			# Use the API transactionId for deduplication, fallback to composite key
			transaction_id = txn.get("transactionId") or f"{plate_string}_{txn.get('date')}_{txn_time}_{amount}"

			# Check if already exists
			if frappe.db.exists("Darb Transaction", {"darb_transaction_id": transaction_id}):
				continue

			# Find the vehicle
			vehicle = _find_vehicle_by_plate(plate_info)
			if not vehicle:
				frappe.logger().info(f"Darb: no vehicle found for plate {plate_string}")
				continue

			darb_doc = frappe.new_doc("Darb Transaction")
			darb_doc.vehicle = vehicle
			darb_doc.transaction_date = txn_date
			darb_doc.transaction_time = txn_time
			darb_doc.gate_location = toll_gate
			darb_doc.toll_amount = amount
			darb_doc.status = "Unpaid"
			darb_doc.sync_date = datetime.now()
			darb_doc.darb_transaction_id = transaction_id
			darb_doc.raw_data = json.dumps(txn)

			darb_doc.insert(ignore_permissions=True)
			new_count += 1
			frappe.logger().info(f"Saved Darb: {darb_doc.name} - {toll_gate} - AED {amount}")

		except Exception as e:
			frappe.log_error(f"Error saving Darb transaction: {str(e)}\nData: {txn}", "Darb Integration")
			continue

	frappe.db.commit()
	return new_count


def sync_before_contract_closure(doc, method=None):
	"""
	Sync Darb data before closing a contract.
	Called from document event hook (before_submit).
	"""
	try:
		vehicle = doc.vehicle if hasattr(doc, "vehicle") else None
		if not vehicle:
			return

		result = sync_darb_data()

		if result.get("status") == "success" and result.get("new_transactions", 0) > 0:
			frappe.msgprint(
				f"Darb data synced: {result.get('new_transactions', 0)} new transactions found",
				indicator="green",
				alert=True,
			)
		elif result.get("status") == "error":
			frappe.msgprint(
				f"Darb sync warning: {result.get('message', 'Unknown error')}",
				indicator="orange",
				alert=True,
			)

	except Exception as e:
		frappe.log_error(title="Darb Integration", message=f"Sync before closure error: {str(e)}")
