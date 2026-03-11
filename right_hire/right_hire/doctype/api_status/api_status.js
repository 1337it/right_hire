// Copyright (c) 2026, Right Hire and contributors
// For license information, please see license.txt

frappe.ui.form.on('API Status', {
	refresh: function(frm) {
		// Add button to trigger manual sync
		if (!frm.is_new() && frm.doc.enabled) {
			frm.add_custom_button(__('Trigger Sync Now'), function() {
				frappe.call({
					method: 'right_hire.right_hire.doctype.api_status.api_status.trigger_manual_sync',
					args: {
						api_name: frm.doc.name
					},
					freeze: true,
					freeze_message: __('Syncing data...'),
					callback: function(r) {
						if (r.message) {
							frappe.msgprint({
								title: __('Sync Result'),
								message: JSON.stringify(r.message, null, 2),
								indicator: 'green'
							});
							frm.reload_doc();
						}
					}
				});
			});
		}

		// Set indicator based on status
		if (frm.doc.status) {
			const indicator_map = {
				'Success': 'green',
				'Failed': 'red',
				'Running': 'blue',
				'Started': 'blue',
				'Idle': 'gray'
			};
			frm.set_indicator(frm.doc.status, indicator_map[frm.doc.status] || 'gray');
		}

		// Show alert if there are consecutive errors
		if (frm.doc.error_count >= 3) {
			frm.dashboard.add_comment(__('Warning: {0} consecutive errors. Please check the error message.', [frm.doc.error_count]), 'red', true);
		}
	}
});
