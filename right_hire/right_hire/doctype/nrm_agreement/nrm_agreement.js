// Copyright (c) 2026, Right Hire and contributors
// For license information, please see license.txt

frappe.ui.form.on('NRM Agreement', {
	refresh: function(frm) {
		// Add Complete button for submitted, active NRMs
		if (frm.doc.docstatus === 1 && frm.doc.status === 'Active') {
			frm.add_custom_button(__('Complete NRM'), function() {
				show_complete_dialog(frm);
			}, __('Actions'));
		}

		// Set query for vehicle - only available vehicles
		frm.set_query('vehicle', function() {
			return {
				filters: {
					'status': ['in', ['Available', 'NRM', '']]
				}
			};
		});

		// Color code status
		if (frm.doc.status === 'Active') {
			frm.set_intro(__('This NRM is currently active'), 'blue');
		} else if (frm.doc.status === 'Completed') {
			frm.set_intro(__('This NRM has been completed'), 'green');
		} else if (frm.doc.status === 'Cancelled') {
			frm.set_intro(__('This NRM has been cancelled'), 'red');
		}
	},

	vehicle: function(frm) {
		if (frm.doc.vehicle) {
			frappe.call({
				method: 'right_hire.right_hire.doctype.nrm_agreement.nrm_agreement.get_vehicle_details',
				args: { vehicle: frm.doc.vehicle },
				callback: function(r) {
					if (r.message) {
						frm.set_value('make_and_model', r.message.make_and_model);
						frm.set_value('vehicle_type', r.message.vehicle_type);
						frm.set_value('vehicle_plate', r.message.vehicle_plate);
						if (!frm.doc.odometer_out && r.message.current_odometer) {
							frm.set_value('odometer_out', r.message.current_odometer);
						}
					}
				}
			});
		}
	},

	assigned_to_type: function(frm) {
		// Clear all assignment fields when type changes
		frm.set_value('staff', '');
		frm.set_value('driver', '');
		frm.set_value('customer', '');
		frm.set_value('other_name', '');
		frm.set_value('assigned_person_name', '');
		frm.set_value('staff_code', '');
		frm.set_value('contact_number', '');
	},

	staff: function(frm) {
		if (frm.doc.staff) {
			frappe.db.get_doc('Employee', frm.doc.staff).then(emp => {
				frm.set_value('assigned_person_name', emp.employee_name);
				frm.set_value('staff_code', emp.name);
				frm.set_value('contact_number', emp.cell_number || emp.personal_email || '');
			});
		}
	},

	driver: function(frm) {
		if (frm.doc.driver) {
			frappe.db.get_doc('Driver', frm.doc.driver).then(driver => {
				frm.set_value('assigned_person_name', driver.full_name || driver.name);
				frm.set_value('staff_code', driver.name);
				frm.set_value('contact_number', driver.cell_number || '');
			});
		}
	},

	customer: function(frm) {
		if (frm.doc.customer) {
			frappe.db.get_doc('Customer', frm.doc.customer).then(customer => {
				frm.set_value('assigned_person_name', customer.customer_name);
				frm.set_value('staff_code', customer.name);
			});
		}
	},

	other_name: function(frm) {
		if (frm.doc.other_name) {
			frm.set_value('assigned_person_name', frm.doc.other_name);
		}
	},

	date_out: function(frm) {
		calculate_days(frm);
	},

	date_in: function(frm) {
		calculate_days(frm);
	},

	odometer_out: function(frm) {
		calculate_km(frm);
	},

	odometer_in: function(frm) {
		calculate_km(frm);
	}
});

function calculate_days(frm) {
	if (frm.doc.date_out) {
		let end_date = frm.doc.date_in || frappe.datetime.now_datetime();
		let days = frappe.datetime.get_day_diff(end_date, frm.doc.date_out) + 1;
		frm.set_value('total_days', Math.max(1, days));
	}
}

function calculate_km(frm) {
	if (frm.doc.odometer_out && frm.doc.odometer_in) {
		let km = frm.doc.odometer_in - frm.doc.odometer_out;
		frm.set_value('km_travelled', Math.max(0, km));
	}
}

function show_complete_dialog(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Complete NRM Agreement'),
		fields: [
			{
				fieldname: 'date_in',
				fieldtype: 'Datetime',
				label: __('Date In'),
				default: frappe.datetime.now_datetime(),
				reqd: 1
			},
			{
				fieldname: 'odometer_in',
				fieldtype: 'Int',
				label: __('Odometer In (KM)'),
				description: __('Current odometer reading')
			},
			{
				fieldname: 'fuel_level_in',
				fieldtype: 'Select',
				label: __('Fuel Level In'),
				options: '\nEmpty\n1/8\n1/4\n3/8\n1/2\n5/8\n3/4\n7/8\nFull'
			}
		],
		primary_action_label: __('Complete'),
		primary_action: function(values) {
			frappe.call({
				method: 'right_hire.right_hire.doctype.nrm_agreement.nrm_agreement.complete_nrm_agreement',
				args: {
					nrm_name: frm.doc.name,
					date_in: values.date_in,
					odometer_in: values.odometer_in,
					fuel_level_in: values.fuel_level_in
				},
				callback: function(r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __('NRM Agreement completed successfully'),
							indicator: 'green'
						});
						frm.reload_doc();
					}
				}
			});
			d.hide();
		}
	});
	d.show();
}
