# Copyright (c) 2026, Right Hire and contributors
# For license information, please see license.txt

import frappe
import requests
import time
from frappe.model.document import Document

class SalikSettings(Document):
	pass

@frappe.whitelist()
def test_api_connection(api_base_url, api_key):
	"""
	Test the Salik API connection by fetching sample trips data
	"""
	try:
		# Build the API endpoint URL
		endpoint = f"{api_base_url.rstrip('/')}/api/trips"

		# Set up headers with API key
		headers = {
			"X-API-Key": api_key,
			"Content-Type": "application/json"
		}

		# Set up query parameters (fetch last 7 days, limit to 10 for testing)
		from datetime import datetime, timedelta
		date_to = datetime.now().strftime("%Y-%m-%d")
		date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

		params = {
			"date_from": date_from,
			"date_to": date_to,
			"limit": 10
		}

		# Track response time
		start_time = time.time()

		# Make the API request
		response = requests.get(
			endpoint,
			headers=headers,
			params=params,
			timeout=30
		)

		# Calculate response time
		response_time = f"{(time.time() - start_time):.2f}s"

		# Check if request was successful
		response.raise_for_status()

		# Parse the response
		data = response.json()

		# Extract details
		trips = data.get("trips", [])
		total = data.get("total", 0)

		# Get sample trip if available
		sample_trip = None
		if trips:
			sample_trip = trips[0]

		return {
			"success": True,
			"details": {
				"total": total,
				"trips_returned": len(trips),
				"response_time": response_time,
				"sample_trip": sample_trip
			}
		}

	except requests.exceptions.ConnectionError as e:
		return {
			"success": False,
			"error": f"Connection error: Unable to reach the API server at {api_base_url}. Please check the URL and network connection."
		}

	except requests.exceptions.Timeout as e:
		return {
			"success": False,
			"error": "Request timeout: The API server took too long to respond. Please try again."
		}

	except requests.exceptions.HTTPError as e:
		status_code = e.response.status_code
		if status_code == 401:
			return {
				"success": False,
				"error": "Authentication failed: Invalid API Key. Please check your X-API-Key."
			}
		elif status_code == 403:
			return {
				"success": False,
				"error": "Access forbidden: Your API Key does not have permission to access this endpoint."
			}
		elif status_code == 404:
			return {
				"success": False,
				"error": "Endpoint not found: The /api/trips endpoint was not found. Please check the API Base URL."
			}
		else:
			return {
				"success": False,
				"error": f"HTTP Error {status_code}: {str(e)}"
			}

	except Exception as e:
		frappe.log_error(f"Salik API Test Error: {str(e)}", "Salik Settings Test Connection")
		return {
			"success": False,
			"error": f"Unexpected error: {str(e)}"
		}
