// Copyright (c) 2026, Right Hire and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salik Settings', {
	refresh: function(frm) {
		// Add custom styling for the test button
		frm.fields_dict.test_connection.$input.addClass('btn-primary');
	},

	test_connection: function(frm) {
		test_salik_api_connection(frm);
	}
});

function test_salik_api_connection(frm) {
	// Validate settings before testing
	if (!frm.doc.api_base_url) {
		frappe.msgprint({
			title: __('Missing Configuration'),
			message: __('Please enter the API Base URL'),
			indicator: 'red'
		});
		return;
	}

	if (!frm.doc.api_key) {
		frappe.msgprint({
			title: __('Missing Configuration'),
			message: __('Please enter the API Key'),
			indicator: 'red'
		});
		return;
	}

	// Show loading indicator
	frappe.dom.freeze(__('Testing API connection...<br><small>Fetching sample trips data</small>'));

	// Call the test connection API
	frappe.call({
		method: 'right_hire.right_hire.doctype.salik_settings.salik_settings.test_api_connection',
		args: {
			api_base_url: frm.doc.api_base_url,
			api_key: frm.doc.api_key
		},
		callback: function(r) {
			frappe.dom.unfreeze();

			if (r.message && r.message.success) {
				// Show success message with details
				let message = __('API Connection Successful!');
				let details = r.message.details;

				if (details) {
					message += '<br><br><div style="text-align: left;">';
					message += `<strong>Total Trips Found:</strong> ${details.total || 0}<br>`;
					message += `<strong>Response Time:</strong> ${details.response_time || 'N/A'}<br>`;

					if (details.sample_trip) {
						message += '<br><strong>Sample Trip:</strong><br>';
						message += `<small>`;
						message += `Date: ${details.sample_trip.trip_date || 'N/A'}<br>`;
						message += `Gate: ${details.sample_trip.gate || 'N/A'}<br>`;
						message += `Cost: AED ${details.sample_trip.cost || 'N/A'}<br>`;
						message += `</small>`;
					}
					message += '</div>';
				}

				frappe.msgprint({
					title: __('Connection Test Successful'),
					message: message,
					indicator: 'green'
				});

				// Show success alert
				frappe.show_alert({
					message: __('API Connection Test Passed'),
					indicator: 'green'
				}, 5);

			} else {
				// Show error message
				let error_message = r.message && r.message.error ? r.message.error : 'Unknown error occurred';

				frappe.msgprint({
					title: __('Connection Test Failed'),
					message: __('Failed to connect to Salik API:<br><br><code>{0}</code>', [error_message]),
					indicator: 'red'
				});
			}
		},
		error: function(err) {
			frappe.dom.unfreeze();

			frappe.msgprint({
				title: __('Connection Error'),
				message: __('An error occurred while testing the API connection. Please check your settings and try again.'),
				indicator: 'red'
			});

			console.error('Salik API Test Error:', err);
		}
	});
}
