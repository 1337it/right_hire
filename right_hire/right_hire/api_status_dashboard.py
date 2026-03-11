"""
API Status Dashboard Widget
Generates HTML for displaying API status in workspace
"""

import frappe
from frappe.utils import get_datetime_str, time_diff_in_hours, get_datetime
from datetime import datetime

@frappe.whitelist()
def get_api_status_html():
	"""Generate HTML for API status dashboard widget"""

	# Get all API statuses
	statuses = frappe.get_all(
		"API Status",
		fields=["name", "api_name", "api_type", "status", "last_sync_time",
		        "last_error_message", "records_fetched", "error_count", "enabled",
		        "next_sync_time", "last_success_time"],
		filters={"enabled": 1}
	)

	if not statuses:
		return """
		<div class="api-status-widget-compact" style="padding: 8px; background: #f8f9fa; border-radius: 6px;">
			<p style="color: #6c757d; margin: 0; font-size: 12px;">No API integrations configured.</p>
		</div>
		"""

	html = """
	<style>
		.api-status-widget-compact {
			padding: 10px;
			background: #ffffff;
			border: 1px solid #e9ecef;
			border-radius: 6px;
		}
		.api-status-compact-row {
			display: flex;
			gap: 8px;
			flex-wrap: wrap;
			align-items: stretch;
		}
		.api-status-item-compact {
			flex: 1;
			min-width: 180px;
			display: flex;
			align-items: center;
			padding: 8px 10px;
			background: #f8f9fa;
			border-radius: 4px;
			border-left: 3px solid #dee2e6;
			gap: 8px;
		}
		.api-status-item-compact.success {
			border-left-color: #28a745;
			background: #f1f9f3;
		}
		.api-status-item-compact.failed {
			border-left-color: #dc3545;
			background: #fef5f5;
		}
		.api-status-item-compact.running {
			border-left-color: #17a2b8;
			background: #f0f8fa;
		}
		.api-status-item-compact.idle {
			border-left-color: #6c757d;
		}
		.api-item-info {
			flex: 1;
		}
		.api-item-name {
			font-weight: 600;
			font-size: 12px;
			color: #2c3e50;
		}
		.api-item-time {
			font-size: 10px;
			color: #6c757d;
		}
		.api-badge-compact {
			padding: 2px 6px;
			border-radius: 8px;
			font-size: 9px;
			font-weight: 600;
			text-transform: uppercase;
		}
		.badge-success { background: #28a745; color: white; }
		.badge-failed { background: #dc3545; color: white; }
		.badge-running { background: #17a2b8; color: white; }
		.badge-idle { background: #6c757d; color: white; }
		.badge-started { background: #ffc107; color: #000; }
		.api-btn-row {
			display: flex;
			gap: 6px;
			margin-top: 8px;
			justify-content: flex-end;
		}
		.api-btn-sm {
			padding: 3px 8px;
			border: none;
			border-radius: 3px;
			cursor: pointer;
			font-size: 10px;
			font-weight: 500;
		}
		.api-btn-sm:disabled {
			opacity: 0.6;
			cursor: not-allowed;
		}
		.btn-refresh-sm {
			background: #6c757d;
			color: white;
		}
		.btn-salik-sm {
			background: #28a745;
			color: white;
		}
		.btn-darb-sm {
			background: #fd7e14;
			color: white;
		}
		.btn-rta-sm {
			background: #dc3545;
			color: white;
		}
		.api-error-compact {
			font-size: 9px;
			color: #856404;
			background: #fff3cd;
			padding: 2px 4px;
			border-radius: 2px;
			margin-top: 2px;
		}
	</style>

	<div class="api-status-widget-compact">
		<div class="api-status-compact-row">
	"""

	for api in statuses:
		status_class = api.status.lower() if api.status else "idle"

		# Format last sync time with relative display
		last_sync = "Never"
		if api.last_sync_time:
			hours_ago = time_diff_in_hours(datetime.now(), api.last_sync_time)
			if hours_ago < 1:
				mins = int(hours_ago * 60)
				last_sync = f"{mins}m ago" if mins > 0 else "Now"
			elif hours_ago < 24:
				last_sync = f"{int(hours_ago)}h ago"
			else:
				last_sync = f"{int(hours_ago / 24)}d ago"

		# Format next sync time
		next_sync = ""
		if api.next_sync_time:
			next_hours = time_diff_in_hours(api.next_sync_time, datetime.now())
			if next_hours < 0:
				next_sync = "pending"
			elif next_hours < 1:
				next_sync = f"in {int(next_hours * 60)}m"
			else:
				next_sync = f"in {int(next_hours)}h"

		# Short API name
		if "Salik" in api.api_name:
			short_name = "Salik"
		elif "Darb" in api.api_name:
			short_name = "Darb"
		else:
			short_name = "RTA"

		html += f"""
			<div class="api-status-item-compact {status_class}">
				<div class="api-item-info">
					<div class="api-item-name">{short_name}</div>
					<div class="api-item-time">{last_sync}{f' · next {next_sync}' if next_sync else ''}</div>
				</div>
				<span class="api-badge-compact badge-{status_class}">{api.status or 'Idle'}</span>
			</div>
		"""

	# Close row and add compact buttons
	html += """
		</div>
		<div class="api-btn-row">
			<button class="api-btn-sm btn-refresh-sm" data-action="refresh-status">↻</button>
			<button class="api-btn-sm btn-salik-sm" data-action="sync-salik">Sync Salik</button>
			<button class="api-btn-sm btn-darb-sm" data-action="sync-darb">Sync Darb</button>
			<button class="api-btn-sm btn-rta-sm" data-action="sync-rta">Sync RTA</button>
		</div>
	</div>
	"""

	return html


@frappe.whitelist()
def get_salik_api_status():
	"""Get Salik API status for number card"""
	api_status = frappe.db.get_value(
		"API Status",
		{"api_type": "Salik Trips", "enabled": 1},
		["status", "last_sync_time", "total_records", "last_error_message"],
		as_dict=True
	)

	if not api_status:
		# Fallback to Salik Settings
		settings = frappe.db.get_value(
			"Salik Settings",
			"Salik Settings",
			["last_successful_sync", "total_transactions_fetched", "last_error_message"],
			as_dict=True
		)
		if settings:
			status = "Success" if settings.last_successful_sync else "Idle"
			last_sync = settings.last_successful_sync
			total = settings.total_transactions_fetched or 0
		else:
			status = "Not Configured"
			last_sync = None
			total = 0
	else:
		status = api_status.status or "Idle"
		last_sync = api_status.last_sync_time
		total = api_status.total_records or 0

	# Format last sync time
	if last_sync:
		hours_ago = time_diff_in_hours(datetime.now(), last_sync)
		if hours_ago < 1:
			sync_text = f"{int(hours_ago * 60)}m ago"
		elif hours_ago < 24:
			sync_text = f"{int(hours_ago)}h ago"
		else:
			sync_text = frappe.utils.format_datetime(last_sync, "dd MMM")
	else:
		sync_text = "Never"

	return {
		"value": total,
		"fieldtype": "Int",
		"label": f"Salik: {status} ({sync_text})",
		"route": ["List", "Salik Transaction"]
	}


@frappe.whitelist()
def sync_salik_now():
	"""Run Salik sync directly and return result"""
	try:
		from right_hire.right_hire.salik_integration import sync_salik_data
		result = sync_salik_data()
		return result or {"status": "success", "message": "Salik sync complete"}
	except Exception as e:
		frappe.log_error(title="Manual Sync", message=f"Salik sync failed: {str(e)}")
		return {"status": "error", "message": str(e)[:200]}


@frappe.whitelist()
def sync_darb_now():
	"""Run Darb sync directly and return result"""
	try:
		from right_hire.right_hire.darb_integration import sync_darb_data
		result = sync_darb_data()
		return result or {"status": "success", "message": "Darb sync complete"}
	except Exception as e:
		frappe.log_error(title="Manual Sync", message=f"Darb sync failed: {str(e)}")
		return {"status": "error", "message": str(e)[:200]}


@frappe.whitelist()
def sync_rta_fines_now():
	"""Run RTA fines sync directly and return result"""
	try:
		from right_hire.right_hire.rta_fines_integration import sync_all_vehicles_fines
		result = sync_all_vehicles_fines()
		return result or {"status": "success", "message": "RTA fines sync complete"}
	except Exception as e:
		frappe.log_error(title="Manual Sync", message=f"RTA fines sync failed: {str(e)}")
		return {"status": "error", "message": str(e)[:200]}


@frappe.whitelist()
def get_traffic_fines_api_status():
	"""Get Traffic Fines API status for number card"""
	api_status = frappe.db.get_value(
		"API Status",
		{"api_type": "RTA Traffic Fines", "enabled": 1},
		["status", "last_sync_time", "total_records", "last_error_message"],
		as_dict=True
	)

	if not api_status:
		# Fallback to RTA Settings
		settings = frappe.db.get_value(
			"RTA Settings",
			"RTA Settings",
			["last_successful_sync", "total_fines_fetched", "last_error_message"],
			as_dict=True
		)
		if settings:
			status = "Success" if settings.last_successful_sync else "Idle"
			last_sync = settings.last_successful_sync
			total = settings.total_fines_fetched or 0
		else:
			status = "Not Configured"
			last_sync = None
			total = 0
	else:
		status = api_status.status or "Idle"
		last_sync = api_status.last_sync_time
		total = api_status.total_records or 0

	# Format last sync time
	if last_sync:
		hours_ago = time_diff_in_hours(datetime.now(), last_sync)
		if hours_ago < 1:
			sync_text = f"{int(hours_ago * 60)}m ago"
		elif hours_ago < 24:
			sync_text = f"{int(hours_ago)}h ago"
		else:
			sync_text = frappe.utils.format_datetime(last_sync, "dd MMM")
	else:
		sync_text = "Never"

	return {
		"value": total,
		"fieldtype": "Int",
		"label": f"RTA Fines: {status} ({sync_text})",
		"route": ["List", "Traffic Fine"]
	}


@frappe.whitelist()
def get_darb_api_status():
	"""Get Darb API status for number card"""
	api_status = frappe.db.get_value(
		"API Status",
		{"api_type": "Darb Tolls", "enabled": 1},
		["status", "last_sync_time", "total_records", "last_error_message"],
		as_dict=True
	)

	if not api_status:
		status = "Not Configured"
		last_sync = None
		total = 0
	else:
		status = api_status.status or "Idle"
		last_sync = api_status.last_sync_time
		total = api_status.total_records or 0

	# Format last sync time
	if last_sync:
		hours_ago = time_diff_in_hours(datetime.now(), last_sync)
		if hours_ago < 1:
			sync_text = f"{int(hours_ago * 60)}m ago"
		elif hours_ago < 24:
			sync_text = f"{int(hours_ago)}h ago"
		else:
			sync_text = frappe.utils.format_datetime(last_sync, "dd MMM")
	else:
		sync_text = "Never"

	return {
		"value": total,
		"fieldtype": "Int",
		"label": f"Darb: {status} ({sync_text})",
		"route": ["List", "Darb Transaction"]
	}
