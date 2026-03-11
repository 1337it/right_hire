// Copyright (c) 2026, Right Hire and contributors
// For license information, please see license.txt

frappe.ui.form.on('RTA Settings', {
	refresh: function(frm) {
		// Add Test Connection button
		if (frm.doc.enabled && frm.doc.api_base_url && frm.doc.api_key) {
			frm.add_custom_button(__('Test API Connection'), function() {
				frappe.call({
					method: 'right_hire.right_hire.doctype.rta_settings.rta_settings.test_api_connection',
					freeze: true,
					freeze_message: __('Testing connection...'),
					callback: function(r) {
						if (r.message && r.message.status === 'success') {
							frappe.show_alert({
								message: __('API connection successful!'),
								indicator: 'green'
							});
							frm.reload_doc();
						} else {
							frappe.msgprint({
								title: __('Connection Failed'),
								message: r.message.message || __('Unknown error'),
								indicator: 'red'
							});
							frm.reload_doc();
						}
					}
				});
			}).addClass('btn-primary');
		}

		// Add Sync Now button
		if (frm.doc.enabled) {
			frm.add_custom_button(__('Sync All Vehicles Now'), function() {
				frappe.confirm(
					__('This will sync traffic fines for all enabled vehicles. This may take several minutes. Continue?'),
					function() {
						frappe.call({
							method: 'right_hire.right_hire.doctype.rta_settings.rta_settings.sync_now',
							freeze: true,
							freeze_message: __('Syncing RTA fines...'),
							callback: function(r) {
								if (r.message) {
									if (r.message.status === 'success') {
										frappe.msgprint({
											title: __('Sync Completed'),
											message: __('Vehicles synced: {0}<br>New fines: {1}<br>Errors: {2}', [
												r.message.vehicles_synced || 0,
												r.message.new_fines || 0,
												r.message.errors ? r.message.errors.length : 0
											]),
											indicator: 'green'
										});

										if (r.message.errors && r.message.errors.length > 0) {
											frappe.msgprint({
												title: __('Sync Errors'),
												message: r.message.errors.join('<br>'),
												indicator: 'orange'
											});
										}
									} else {
										frappe.msgprint({
											title: __('Sync Failed'),
											message: r.message.message || __('Unknown error'),
											indicator: 'red'
										});
									}
									frm.reload_doc();
								}
							}
						});
					}
				);
			}).addClass('btn-success');
		}

		// Set indicator based on connection status
		if (frm.doc.connection_status) {
			if (frm.doc.connection_status.includes('✅')) {
				frm.dashboard.set_headline(__('API Status: <span class="indicator green">Connected</span>'));
			} else if (frm.doc.connection_status.includes('❌')) {
				frm.dashboard.set_headline(__('API Status: <span class="indicator red">Disconnected</span>'));
			}
		}

		// Show warning if disabled
		if (!frm.doc.enabled) {
			frm.dashboard.set_headline(__('RTA Integration is <span class="indicator red">Disabled</span>'));
		}
	},

	test_connection: function(frm) {
		// This is triggered when the Test Connection button field is clicked
		frappe.call({
			method: 'right_hire.right_hire.doctype.rta_settings.rta_settings.test_api_connection',
			freeze: true,
			freeze_message: __('Testing connection...'),
			callback: function(r) {
				if (r.message && r.message.status === 'success') {
					frappe.show_alert({
						message: __('API connection successful!'),
						indicator: 'green'
					});
					frm.reload_doc();
				} else {
					frappe.msgprint({
						title: __('Connection Failed'),
						message: r.message.message || __('Unknown error'),
						indicator: 'red'
					});
					frm.reload_doc();
				}
			}
		});
	},

	enabled: function(frm) {
		// Show/hide warnings when enabling/disabling
		if (frm.doc.enabled) {
			if (!frm.doc.api_key || !frm.doc.api_base_url) {
				frappe.msgprint(__('Please configure API Base URL and API Key'));
			}
		}
	}
});
