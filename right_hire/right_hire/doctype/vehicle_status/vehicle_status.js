// Copyright (c) 2024, Right Hire and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Status', {
	refresh: function(frm) {
		// Show color preview
		if (frm.doc.color) {
			frm.get_field('color').$wrapper.find('select').css({
				'background-color': get_color_code(frm.doc.color),
				'color': ['yellow', 'green', 'gray'].includes(frm.doc.color) ? '#000' : '#fff'
			});
		}
	},

	color: function(frm) {
		frm.get_field('color').$wrapper.find('select').css({
			'background-color': get_color_code(frm.doc.color),
			'color': ['yellow', 'green', 'gray'].includes(frm.doc.color) ? '#000' : '#fff'
		});
	}
});

function get_color_code(color) {
	const colors = {
		'gray': '#6c757d',
		'green': '#28a745',
		'blue': '#007bff',
		'orange': '#fd7e14',
		'red': '#dc3545',
		'purple': '#6f42c1',
		'yellow': '#ffc107',
		'pink': '#e83e8c'
	};
	return colors[color] || '#6c757d';
}
