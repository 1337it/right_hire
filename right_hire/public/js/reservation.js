frappe.ui.form.on('Reservation', {
    refresh: function(frm) {
        if (!frm.is_new() && (frm.doc.reservation_status === 'Confirmed' || frm.doc.reservation_status === 'Allocated')) {
            frm.add_custom_button(__('Convert to Agreement'), function() {
                frappe.call({
                    method: 'right_hire.api.reservation.convert_to_agreement',
                    args: {reservation: frm.doc.name},
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.set_route('Form', 'Rental Agreement', r.message.agreement);
                        }
                    }
                });
            }).addClass('btn-primary');
        }
    }
});
