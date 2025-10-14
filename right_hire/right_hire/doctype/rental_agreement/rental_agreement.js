frappe.ui.form.on('Rental Agreement', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // Start Rental button
            if (frm.doc.agreement_status === 'Draft') {
                frm.add_custom_button(__('Start Rental'), function() {
                    show_start_rental_dialog(frm);
                }).addClass('btn-primary');
            }

            // Return Vehicle button
            if (frm.doc.agreement_status === 'Active') {
                frm.add_custom_button(__('Return Vehicle'), function() {
                    show_return_vehicle_dialog(frm);
                }).addClass('btn-primary');
            }

            // Close Agreement button
            if (frm.doc.agreement_status === 'Returned') {
                frm.add_custom_button(__('Close Agreement'), function() {
                    frappe.confirm(
                        __('Are you sure you want to close this agreement?'),
                        function() {
                            frappe.call({
                                method: 'right_hire.api.rental_agreement.close_agreement',
                                args: { agreement: frm.doc.name },
                                callback: function(r) {
                                    if (r.message && r.message.success) {
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }
                    );
                }).addClass('btn-success');
            }

            // Add Charge button
            if (frm.doc.agreement_status !== 'Closed' && frm.doc.agreement_status !== 'Cancelled') {
                frm.add_custom_button(__('Add Charge'), function() {
                    show_add_charge_dialog(frm);
                });
            }
        }

        // Status indicator
        if (frm.doc.agreement_status) {
            frm.dashboard.add_indicator(
                __('Status: {0}', [frm.doc.agreement_status]),
                get_agreement_status_color(frm.doc.agreement_status)
            );
        }

        // Outstanding indicator
        if (frm.doc.outstanding_amount > 0) {
            // If format_currency isn't available, fallback:
            const formatted = (typeof format_currency === 'function')
                ? format_currency(frm.doc.outstanding_amount)
                : frappe.format(frm.doc.outstanding_amount, { fieldtype: 'Currency' });
            frm.dashboard.add_indicator(__('Outstanding: {0}', [formatted]), 'red');
        }
    },

    odometer_in: function(frm) {
        if (frm.doc.odometer_in && frm.doc.odometer_out) {
            let km_driven = frm.doc.odometer_in - frm.doc.odometer_out;
            frm.set_value('km_driven', km_driven);

            if (frm.doc.free_km && km_driven > frm.doc.free_km) {
                frm.set_value('overage_km', km_driven - frm.doc.free_km);
            }
        }
    }
});

frappe.ui.form.on('Agreement Charge', {
    qty: function(frm, cdt, cdn) {
        calculate_charge_amount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_charge_amount(frm, cdt, cdn);
    },
    charges_remove: function(frm) {
        frm.trigger('calculate_totals');
    }
});

function calculate_charge_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.qty) * flt(row.rate);
    frm.refresh_field('charges');
    frm.trigger('calculate_totals');
}

function get_agreement_status_color(status) {
    const color_map = {
        'Draft': 'gray',
        'Active': 'green',
        'Due for Return': 'orange',
        'Returned': 'blue',
        'Closed': 'darkgray',
        'Cancelled': 'red'
    };
    return color_map[status] || 'blue';
}

function show_start_rental_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Start Rental'),
        fields: [
            { fieldname: 'odometer_out', label: __('Odometer Reading (KM)'), fieldtype: 'Int', reqd: 1, default: frm.doc.odometer_out },
            { fieldname: 'fuel_out', label: __('Fuel Level (%)'), fieldtype: 'Percent', reqd: 1, default: frm.doc.fuel_out || 100 }
        ],
        primary_action_label: __('Start'),
        primary_action: function(values) {
            frappe.call({
                method: 'right_hire.api.rental_agreement.start_rental',
                args: {
                    agreement: frm.doc.name,
                    odometer_out: values.odometer_out,
                    fuel_out: values.fuel_out
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        d.hide();
                    }
                }
            });
        }
    });
    d.show();
}

function show_return_vehicle_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Return Vehicle'),
        fields: [
            { fieldname: 'odometer_in', label: __('Odometer Reading (KM)'), fieldtype: 'Int', reqd: 1 },
            { fieldname: 'fuel_in', label: __('Fuel Level (%)'), fieldtype: 'Percent', reqd: 1 }
        ],
        primary_action_label: __('Return'),
        primary_action: function(values) {
            frappe.call({
                method: 'right_hire.api.rental_agreement.return_vehicle',
                args: {
                    agreement: frm.doc.name,
                    odometer_in: values.odometer_in,
                    fuel_in: values.fuel_in
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        d.hide();
                        const formatted = (typeof format_currency === 'function')
                            ? format_currency(r.message.outstanding)
                            : frappe.format(r.message.outstanding, { fieldtype: 'Currency' });
                        frappe.msgprint(__('Outstanding amount: {0}', [formatted]));
                    }
                }
            });
        }
    });
    d.show();
}

function show_add_charge_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Add Charge'),
        fields: [
            {
                fieldname: 'charge_type',
                label: __('Charge Type'),
                fieldtype: 'Select',
                options: 'Fuel\nCleaning\nDamage\nToll\nFine\nLate Fee\nOther',
                reqd: 1
            },
            { fieldname: 'description', label: __('Description'), fieldtype: 'Small Text', reqd: 1 },
            { fieldname: 'amount', label: __('Amount'), fieldtype: 'Currency', reqd: 1 }
        ],
        primary_action_label: __('Add'),
        primary_action: function(values) {
            frappe.call({
                method: 'right_hire.api.rental_agreement.add_charge',
                args: {
                    agreement: frm.doc.name,
                    charge_type: values.charge_type,
                    description: values.description,
                    amount: values.amount
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        d.hide();
                    }
                }
            });
        }
    });
    d.show();
}
