"""
Notification System for Salik and Traffic Fines
Sends email alerts for new fines and high-value charges
"""

import frappe
from frappe import _
from frappe.utils import flt, get_url_to_form

def send_new_fines_notification(fines):
	"""
	Send email notification for newly detected traffic fines
	"""
	rta_settings = frappe.get_single("RTA Settings")

	if not rta_settings.notify_on_new_fines or not rta_settings.notification_recipients:
		return

	if not fines:
		return

	# Parse recipients
	recipients = [email.strip() for email in rta_settings.notification_recipients.split(",")]

	# Prepare email content
	subject = _("New Traffic Fines Detected - {0} Fine(s)").format(len(fines))

	message = """
	<h3>New Traffic Fines Detected</h3>
	<p>The following traffic fines were detected during the latest sync:</p>

	<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
		<thead>
			<tr style="background-color: #f0f0f0;">
				<th>Fine Number</th>
				<th>Vehicle</th>
				<th>Date</th>
				<th>Location</th>
				<th>Amount (AED)</th>
				<th>Black Points</th>
				<th>Source</th>
			</tr>
		</thead>
		<tbody>
	"""

	total_amount = 0
	for fine in fines:
		fine_url = get_url_to_form("Traffic Fine", fine.get("name"))
		total_amount += flt(fine.get("amount", 0))

		message += f"""
		<tr>
			<td><a href="{fine_url}">{fine.get("fine_number", "N/A")}</a></td>
			<td>{fine.get("vehicle", "N/A")}</td>
			<td>{fine.get("fine_date", "N/A")}</td>
			<td>{fine.get("location", "N/A")[:50]}...</td>
			<td style="text-align: right;">{flt(fine.get("amount", 0)):.2f}</td>
			<td style="text-align: center;">{fine.get("black_points") or "-"}</td>
			<td>{fine.get("source", "N/A")}</td>
		</tr>
		"""

	message += f"""
		</tbody>
		<tfoot>
			<tr style="background-color: #f9f9f9; font-weight: bold;">
				<td colspan="4">Total</td>
				<td style="text-align: right;">{total_amount:.2f} AED</td>
				<td colspan="2"></td>
			</tr>
		</tfoot>
	</table>

	<p style="margin-top: 20px;">
		Please review and take necessary action on these fines.
	</p>

	<p style="font-size: 12px; color: #666;">
		This is an automated notification from Right Hire RTA Integration.
	</p>
	"""

	# Send email
	try:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			delayed=False
		)
		frappe.logger().info(f"Sent new fines notification to {len(recipients)} recipients")
	except Exception as e:
		frappe.log_error(f"Failed to send fines notification: {str(e)}", "Notifications")


def send_high_value_fine_alert(fine):
	"""
	Send email alert for high-value traffic fine
	"""
	rta_settings = frappe.get_single("RTA Settings")

	if not rta_settings.notify_on_high_value_fines or not rta_settings.notification_recipients:
		return

	fine_amount = flt(fine.get("amount", 0))
	threshold = flt(rta_settings.high_value_threshold or 1000)

	if fine_amount < threshold:
		return

	# Parse recipients
	recipients = [email.strip() for email in rta_settings.notification_recipients.split(",")]

	# Prepare email content
	subject = _("⚠️ High Value Traffic Fine Alert - {0} AED").format(fine_amount)

	fine_url = get_url_to_form("Traffic Fine", fine.get("name"))

	message = f"""
	<h3 style="color: #d9534f;">⚠️ High Value Traffic Fine Detected</h3>

	<p>A high-value traffic fine exceeding the threshold of <strong>{threshold} AED</strong> has been detected:</p>

	<table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse;">
		<tr>
			<th style="background-color: #f0f0f0; text-align: left;">Fine Number</th>
			<td><a href="{fine_url}">{fine.get("fine_number", "N/A")}</a></td>
		</tr>
		<tr>
			<th style="background-color: #f0f0f0; text-align: left;">Vehicle</th>
			<td>{fine.get("vehicle", "N/A")}</td>
		</tr>
		<tr>
			<th style="background-color: #f0f0f0; text-align: left;">Date & Time</th>
			<td>{fine.get("fine_date", "N/A")} {fine.get("fine_time", "")}</td>
		</tr>
		<tr>
			<th style="background-color: #f0f0f0; text-align: left;">Location</th>
			<td>{fine.get("location", "N/A")}</td>
		</tr>
		<tr>
			<th style="background-color: #f0f0f0; text-align: left;">Amount</th>
			<td style="color: #d9534f; font-size: 16px; font-weight: bold;">{fine_amount:.2f} AED</td>
		</tr>
		<tr>
			<th style="background-color: #f0f0f0; text-align: left;">Black Points</th>
			<td>{fine.get("black_points") or "None"}</td>
		</tr>
		<tr>
			<th style="background-color: #f0f0f0; text-align: left;">Source</th>
			<td>{fine.get("source", "N/A")}</td>
		</tr>
		<tr>
			<th style="background-color: #f0f0f0; text-align: left;">Details</th>
			<td>{fine.get("details", "N/A")}</td>
		</tr>
	</table>

	<p style="margin-top: 20px;">
		<strong>Immediate action may be required.</strong> Please review this fine and take appropriate steps.
	</p>

	<p style="font-size: 12px; color: #666;">
		This is an automated high-value alert from Right Hire RTA Integration.
	</p>
	"""

	# Send email
	try:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			delayed=False
		)
		frappe.logger().info(f"Sent high-value fine alert to {len(recipients)} recipients")
	except Exception as e:
		frappe.log_error(f"Failed to send high-value alert: {str(e)}", "Notifications")


def send_new_salik_charges_notification(transactions):
	"""
	Send email notification for newly detected Salik charges
	Optional - can be enabled in Salik Settings if needed
	"""
	if not transactions:
		return

	salik_settings = frappe.get_single("Salik Settings")

	# Check if Salik also has notification settings (would need to add these fields)
	if not hasattr(salik_settings, "notify_on_new_charges") or not salik_settings.get("notify_on_new_charges"):
		return

	# Prepare email content similar to fines notification
	subject = _("New Salik Charges Detected - {0} Transaction(s)").format(len(transactions))

	message = """
	<h3>New Salik Toll Charges Detected</h3>
	<p>The following Salik toll charges were detected during the latest sync:</p>

	<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
		<thead>
			<tr style="background-color: #f0f0f0;">
				<th>Vehicle</th>
				<th>Date</th>
				<th>Time</th>
				<th>Gate Location</th>
				<th>Amount (AED)</th>
			</tr>
		</thead>
		<tbody>
	"""

	total_amount = 0
	for trans in transactions:
		trans_url = get_url_to_form("Salik Transaction", trans.get("name"))
		total_amount += flt(trans.get("toll_amount", 0))

		message += f"""
		<tr>
			<td><a href="{trans_url}">{trans.get("vehicle", "N/A")}</a></td>
			<td>{trans.get("transaction_date", "N/A")}</td>
			<td>{trans.get("transaction_time", "N/A")}</td>
			<td>{trans.get("gate_location", "N/A")}</td>
			<td style="text-align: right;">{flt(trans.get("toll_amount", 0)):.2f}</td>
		</tr>
		"""

	message += f"""
		</tbody>
		<tfoot>
			<tr style="background-color: #f9f9f9; font-weight: bold;">
				<td colspan="4">Total</td>
				<td style="text-align: right;">{total_amount:.2f} AED</td>
			</tr>
		</tfoot>
	</table>

	<p style="margin-top: 20px;">
		These charges have been recorded in the system.
	</p>

	<p style="font-size: 12px; color: #666;">
		This is an automated notification from Right Hire Salik Integration.
	</p>
	"""

	# Would send email if notification settings exist
	# frappe.sendmail(...)


def check_and_send_notifications_after_sync():
	"""
	Check for new fines/charges after sync and send notifications
	This should be called after sync completes
	"""
	# Get fines added in last sync
	rta_settings = frappe.get_single("RTA Settings")

	if rta_settings.notify_on_new_fines and rta_settings.notification_recipients:
		# Get recent fines (last 1 hour)
		recent_fines = frappe.get_all(
			"Traffic Fine",
			filters={
				"creation": [">=", frappe.utils.add_to_date(None, hours=-1)]
			},
			fields=["name", "vehicle", "fine_number", "fine_date", "location",
			        "amount", "black_points", "source", "details"]
		)

		if recent_fines:
			send_new_fines_notification(recent_fines)

			# Check for high-value fines
			if rta_settings.notify_on_high_value_fines:
				threshold = flt(rta_settings.high_value_threshold or 1000)
				for fine in recent_fines:
					if flt(fine.get("amount", 0)) >= threshold:
						send_high_value_fine_alert(fine)


@frappe.whitelist()
def test_notification(notification_type="new_fines"):
	"""
	Test notification system with sample data
	"""
	if notification_type == "new_fines":
		# Send test with sample data
		sample_fines = [{
			"name": "TEST-FINE-001",
			"vehicle": "TEST-VEH-001",
			"fine_number": "500250215714",
			"fine_date": "2026-01-09",
			"location": "Test Location - Sharjah",
			"amount": 500,
			"black_points": 4,
			"source": "Sharjah Traffic",
			"details": "Test fine for notification"
		}]
		send_new_fines_notification(sample_fines)
		return {"status": "success", "message": "Test notification sent"}

	elif notification_type == "high_value":
		sample_fine = {
			"name": "TEST-FINE-HV-001",
			"vehicle": "TEST-VEH-001",
			"fine_number": "500250215715",
			"fine_date": "2026-01-09",
			"fine_time": "15:30",
			"location": "Test Location - Dubai",
			"amount": 3000,
			"black_points": 12,
			"source": "Dubai Traffic",
			"details": "Test high-value fine for notification"
		}
		send_high_value_fine_alert(sample_fine)
		return {"status": "success", "message": "Test high-value alert sent"}
