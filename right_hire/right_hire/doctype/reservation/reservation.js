frappe.ui.form.on('Reservation', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // Convert to Agreement button
            if (frm.doc.reservation_status === 'Confirmed' || frm.doc.reservation_status === 'Allocated') {
                frm.add_custom_button(__('Convert to Agreement'), function() {
                    frappe.call({
                        method: 'right_hire.api.reservation.convert_to_agreement',
                        args: { reservation: frm.doc.name },
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint(__('Agreement {0} created', [r.message.agreement]));
                                frm.reload_doc();
                                frappe.set_route('Form', 'Rental Agreement', r.message.agreement);
                            }
                        }
                    });
                }).addClass('btn-primary');
            }

            // Suggest vehicles button
            if (!frm.doc.vehicle && frm.doc.pickup_datetime && frm.doc.return_datetime) {
                frm.add_custom_button(__('Suggest Vehicles'), function() {
                    leet_rental.utils.show_vehicle_selector(
                        {
                            start_datetime: frm.doc.pickup_datetime,
                            end_datetime: frm.doc.return_datetime,
                            branch: frm.doc.branch
                        },
                        function(vehicle) {
                            frm.set_value('vehicle', vehicle);
                        }
                    );
                });
            }
        }
    },

    pickup_datetime: function(frm) {
        calculate_rental_days(frm);
        check_vehicle_availability(frm);
    },

    return_datetime: function(frm) {
        calculate_rental_days(frm);
        check_vehicle_availability(frm);
    },

    vehicle: function(frm) {
        check_vehicle_availability(frm);
    },

    rate_plan: function(frm) {
        if (frm.doc.rate_plan) {
            frappe.db.get_doc('Rate Plan', frm.doc.rate_plan).then(rate_plan => {
                frm.set_value('base_rate', rate_plan.base_rate);
                frm.set_value('deposit', rate_plan.deposit);
                calculate_amounts(frm);
            });
        }
    }
});

frappe.ui.form.on('Reservation Extra', {
    qty: function(frm, cdt, cdn) {
        calculate_extra_amount(frm, cdt, cdn);
    },

    rate: function(frm, cdt, cdn) {
        calculate_extra_amount(frm, cdt, cdn);
    },

    extras_remove: function(frm) {
        calculate_amounts(frm);
    }
});

function calculate_rental_days(frm) {
    if (frm.doc.pickup_datetime && frm.doc.return_datetime) {
        // Using moment as in your original; dayjs is also available in newer Frappe versions.
        let start = moment(frm.doc.pickup_datetime);
        let end = moment(frm.doc.return_datetime);
        let hours = end.diff(start, 'hours', true); // true = float precision
        frm.set_value('rental_days', hours / 24);
        calculate_amounts(frm);
    }
}

function calculate_extra_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.qty) * flt(row.rate);
    frm.refresh_field('extras');
    calculate_amounts(frm);
}

function calculate_amounts(frm) {
    if (frm.doc.base_rate && frm.doc.rental_days) {
        frm.set_value('rental_amount', flt(frm.doc.base_rate) * flt(frm.doc.rental_days));
    }

    let extras_total = 0;
    (frm.doc.extras || []).forEach(function(extra) {
        extras_total += flt(extra.amount);
    });
    frm.set_value('extras_total', extras_total);

    frm.set_value('grand_total', flt(frm.doc.rental_amount) + extras_total);
}

function check_vehicle_availability(frm) {
    if (frm.doc.vehicle && frm.doc.pickup_datetime && frm.doc.return_datetime) {
        leet_rental.utils.check_vehicle_availability(
            frm.doc.vehicle,
            frm.doc.pickup_datetime,
            frm.doc.return_datetime,
            function(result) {
                if (!result.available) {
                    frappe.msgprint({
                        title: __('Vehicle Not Available'),
                        message: __('Vehicle {0} is not available for the selected period', [frm.doc.vehicle]),
                        indicator: 'red'
                    });
                }
            }
        );
    }
}
