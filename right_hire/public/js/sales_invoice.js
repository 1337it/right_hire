// Sales Invoice customizations for Right Hire
// Adds Salik toll charges functionality
console.log("Right Hire Sales Invoice JS loaded");

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		console.log("Sales Invoice refresh triggered", frm.doc.vehicle, frm.doc.lease_agreement);
		// Add button to fetch Salik charges if invoice is draft and has vehicle/agreement
		if (frm.doc.docstatus === 0) {
			add_salik_button(frm);
		}
	},

	vehicle(frm) {
		// When vehicle changes, show Salik summary if available
		if (frm.doc.vehicle) {
			show_salik_summary(frm);
		}
	},

	lease_agreement(frm) {
		if (frm.doc.lease_agreement) {
			show_salik_summary(frm);
		}
	},

	rental_agreement(frm) {
		if (frm.doc.rental_agreement) {
			show_salik_summary(frm);
		}
	}
});

function add_salik_button(frm) {
	console.log("add_salik_button called", {
		vehicle: frm.doc.vehicle,
		lease: frm.doc.lease_agreement,
		rental: frm.doc.rental_agreement
	});
	// Check if vehicle or agreement is linked
	if (frm.doc.vehicle || frm.doc.lease_agreement || frm.doc.rental_agreement) {
		console.log("Adding Fetch Salik Charges button");
		frm.add_custom_button(__('Fetch Salik Charges'), function() {
			fetch_salik_charges(frm);
		}).addClass('btn-primary');
	}
}

function show_salik_summary(frm) {
	frappe.call({
		method: 'right_hire.right_hire.salik_invoice.get_salik_summary',
		args: {
			vehicle: frm.doc.vehicle || null,
			lease_agreement: frm.doc.lease_agreement || null,
			rental_agreement: frm.doc.rental_agreement || null
		},
		callback: function(r) {
			if (r.message && r.message.total_trips > 0) {
				let msg = `<b>${r.message.total_trips}</b> pending Salik trips found<br>`;
				msg += `Base amount: AED ${r.message.total_base_amount.toFixed(2)}<br>`;
				msg += `With ${r.message.markup_percent}% markup: AED ${r.message.total_with_markup.toFixed(2)}`;

				frappe.show_alert({
					message: msg,
					indicator: 'blue'
				}, 7);
			}
		}
	});
}

function fetch_salik_charges(frm) {
	// First get summary to show confirmation
	frappe.call({
		method: 'right_hire.right_hire.salik_invoice.get_salik_summary',
		args: {
			vehicle: frm.doc.vehicle || null,
			lease_agreement: frm.doc.lease_agreement || null,
			rental_agreement: frm.doc.rental_agreement || null
		},
		callback: function(r) {
			if (!r.message || r.message.total_trips === 0) {
				frappe.msgprint(__('No pending Salik transactions found for this vehicle/agreement.'));
				return;
			}

			let summary = r.message;
			let details = `<table class="table table-bordered table-sm">
				<thead>
					<tr>
						<th>Schedule</th>
						<th>Trips</th>
						<th>Base Rate</th>
						<th>Rate (+${summary.markup_percent}%)</th>
						<th>Amount</th>
					</tr>
				</thead>
				<tbody>`;

			for (let item of summary.by_schedule) {
				details += `<tr>
					<td><b>${item.schedule}</b></td>
					<td>${item.trips}</td>
					<td>AED ${item.base_rate.toFixed(2)}</td>
					<td>AED ${item.rate_with_markup.toFixed(2)}</td>
					<td>AED ${item.amount.toFixed(2)}</td>
				</tr>`;
			}

			details += `</tbody>
				<tfoot>
					<tr class="table-active">
						<th>Total</th>
						<th>${summary.total_trips}</th>
						<th></th>
						<th></th>
						<th>AED ${summary.total_with_markup.toFixed(2)}</th>
					</tr>
				</tfoot>
			</table>`;

			frappe.confirm(
				__('Add the following Salik charges to this invoice?') + '<br><br>' + details,
				function() {
					// Yes - add items
					add_salik_items(frm);
				},
				function() {
					// No - cancel
				}
			);
		}
	});
}

function add_salik_items(frm) {
	// Save first if dirty
	if (frm.is_dirty()) {
		frm.save().then(() => {
			do_add_salik_items(frm);
		});
	} else {
		do_add_salik_items(frm);
	}
}

function do_add_salik_items(frm) {
	frappe.call({
		method: 'right_hire.right_hire.salik_invoice.add_salik_items_to_invoice',
		args: {
			sales_invoice: frm.doc.name,
			vehicle: frm.doc.vehicle || null,
			lease_agreement: frm.doc.lease_agreement || null,
			rental_agreement: frm.doc.rental_agreement || null
		},
		freeze: true,
		freeze_message: __('Adding Salik charges...'),
		callback: function(r) {
			if (r.message) {
				frm.reload_doc();
				frappe.show_alert({
					message: __('Added {0} Salik item(s), linked {1} transaction(s)', [r.message.added, r.message.transactions_linked]),
					indicator: 'green'
				}, 5);
			}
		}
	});
}
