// Copyright (c) 2026, Right Hire and contributors
// For license information, please see license.txt

frappe.ui.form.on('Traffic Fine', {
	refresh: function(frm) {
		// Add custom buttons if needed
		if (!frm.is_new() && !frm.doc.paid) {
			frm.add_custom_button(__('Mark as Paid'), function() {
				frm.set_value('paid', 1);
				frm.set_value('paid_date', frappe.datetime.get_today());
			});
		}

		// Add button to link to contract if not already linked
		if (!frm.is_new() && !frm.doc.linked_contract && !frm.doc.linked_agreement) {
			frm.add_custom_button(__('Link to Contract'), function() {
				frm.trigger('auto_link_contract');
			});
		}
	},

	auto_link_contract: function(frm) {
		frappe.call({
			method: 'auto_link_contract',
			doc: frm.doc,
			callback: function(r) {
				frm.refresh();
			}
		});
	}
});
