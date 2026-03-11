// Copyright (c) 2026, Right Hire and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Expense', {
	refresh: function(frm) {
		// Add button to create Purchase Invoice
		if (frm.doc.docstatus === 0 && !frm.doc.purchase_invoice && frm.doc.supplier) {
			frm.add_custom_button(__('Create Purchase Invoice'), function() {
				frappe.call({
					method: 'create_purchase_invoice',
					doc: frm.doc,
					callback: function(r) {
						if (r.message) {
							frm.reload_doc();
							frappe.set_route('Form', 'Purchase Invoice', r.message);
						}
					}
				});
			});
		}

		// Add button to view linked Purchase Invoice
		if (frm.doc.purchase_invoice) {
			frm.add_custom_button(__('View Purchase Invoice'), function() {
				frappe.set_route('Form', 'Purchase Invoice', frm.doc.purchase_invoice);
			});
		}
	},

	amount_before_vat: function(frm) {
		calculate_amounts(frm);
	},

	vat_rate: function(frm) {
		calculate_amounts(frm);
	}
});

function calculate_amounts(frm) {
	// Calculate VAT amount
	let vat_amount = (frm.doc.amount_before_vat || 0) * (frm.doc.vat_rate || 0) / 100;
	frm.set_value('vat_amount', vat_amount);

	// Calculate total amount
	let total_amount = (frm.doc.amount_before_vat || 0) + vat_amount;
	frm.set_value('total_amount', total_amount);
}

// Child table calculations
frappe.ui.form.on('Vehicle Expense Item', {
	amount_before_vat: function(frm, cdt, cdn) {
		calculate_item_amounts(frm, cdt, cdn);
	},

	vat_rate: function(frm, cdt, cdn) {
		calculate_item_amounts(frm, cdt, cdn);
	},

	expense_items_remove: function(frm) {
		calculate_totals_from_items(frm);
	}
});

function calculate_item_amounts(frm, cdt, cdn) {
	let row = locals[cdt][cdn];

	// Calculate VAT for this row
	let vat_amount = (row.amount_before_vat || 0) * (row.vat_rate || 0) / 100;
	frappe.model.set_value(cdt, cdn, 'vat_amount', vat_amount);

	// Calculate total for this row
	let total = (row.amount_before_vat || 0) + vat_amount;
	frappe.model.set_value(cdt, cdn, 'total_amount', total);

	// Update parent totals
	calculate_totals_from_items(frm);
}

function calculate_totals_from_items(frm) {
	if (!frm.doc.expense_items || frm.doc.expense_items.length === 0) {
		return;
	}

	let total_before_vat = 0;
	let total_vat = 0;
	let grand_total = 0;

	frm.doc.expense_items.forEach(function(item) {
		total_before_vat += (item.amount_before_vat || 0);
		total_vat += (item.vat_amount || 0);
		grand_total += (item.total_amount || 0);
	});

	frm.set_value('amount_before_vat', total_before_vat);
	frm.set_value('vat_amount', total_vat);
	frm.set_value('total_amount', grand_total);
}
