// Copyright (c) 2026, Right Hire and contributors
// For license information, please see license.txt

frappe.listview_settings['NRM Agreement'] = {
	add_fields: ['status', 'movement_type', 'vehicle', 'assigned_person_name', 'date_out', 'date_in'],

	get_indicator: function(doc) {
		if (doc.status === 'Active') {
			return [__('Active'), 'blue', 'status,=,Active'];
		} else if (doc.status === 'Completed') {
			return [__('Completed'), 'green', 'status,=,Completed'];
		} else if (doc.status === 'Cancelled') {
			return [__('Cancelled'), 'red', 'status,=,Cancelled'];
		}
	},

	formatters: {
		vehicle: function(value, df, doc) {
			if (value) {
				return `<a href="/app/vehicle/${value}">${doc.vehicle_plate || value}</a>`;
			}
			return value;
		}
	},

	onload: function(listview) {
		// Add "New NRM" button
		listview.page.add_inner_button(__('New Staff Movement'), function() {
			frappe.new_doc('NRM Agreement', {
				movement_type: 'Staff Movement',
				assigned_to_type: 'Staff'
			});
		});

		listview.page.add_inner_button(__('New Workshop Movement'), function() {
			frappe.new_doc('NRM Agreement', {
				movement_type: 'Workshop Movement',
				assigned_to_type: 'Other'
			});
		});
	}
};
