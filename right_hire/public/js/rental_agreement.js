frappe.ui.form.on('Rental Agreement', {
    setup: function(frm) {
        // Filter vehicle field to only show available vehicles
        frm.set_query('vehicle', function() {
            return {
                filters: {
                    'status': 'Available'
                }
            };
        });
    },

    refresh: function(frm) {
        if (!frm.is_new()) {
            if (frm.doc.agreement_status === 'Draft') {
                frm.add_custom_button(__('Start Rental'), function() {
                    frappe.prompt([
                        {fieldname: 'odometer_out', label: __('Odometer (KM)'), fieldtype: 'Int', reqd: 1},
                        {fieldname: 'fuel_out', label: __('Fuel Level (%)'), fieldtype: 'Percent', reqd: 1}
                    ], function(values) {
                        frappe.call({
                            method: 'right_hire.api.rental_agreement.start_rental',
                            args: {agreement: frm.doc.name, odometer_out: values.odometer_out, fuel_out: values.fuel_out},
                            callback: function(r) { if (r.message && r.message.success) frm.reload_doc(); }
                        });
                    }, __('Start Rental'));
                }).addClass('btn-primary');
            }

            if (frm.doc.agreement_status === 'Active') {
                frm.add_custom_button(__('Return Vehicle'), function() {
                    frappe.prompt([
                        {fieldname: 'odometer_in', label: __('Odometer (KM)'), fieldtype: 'Int', reqd: 1},
                        {fieldname: 'fuel_in', label: __('Fuel Level (%)'), fieldtype: 'Percent', reqd: 1}
                    ], function(values) {
                        frappe.call({
                            method: 'right_hire.api.rental_agreement.return_vehicle',
                            args: {agreement: frm.doc.name, odometer_in: values.odometer_in, fuel_in: values.fuel_in},
                            callback: function(r) { if (r.message && r.message.success) frm.reload_doc(); }
                        });
                    }, __('Return Vehicle'));
                }).addClass('btn-primary');

                // Add Create Movement button for active agreements
                frm.add_custom_button(__('Create Movement'), function() {
                    show_create_movement_dialog(frm, 'Rental Agreement');
                }, __('Actions'));

                // Add Vehicle Replacement button
                frm.add_custom_button(__('Vehicle Replacement'), function() {
                    show_replacement_dialog(frm, 'Rental Agreement');
                }, __('Actions'));
            }
        }
    }
});

// Create Movement Dialog - shared function for agreements
function show_create_movement_dialog(frm, agreement_type) {
    let movement_types = [
        'NRM - Customer Movement',
        'Delivery',
        'Recovery',
        'Workshop',
        'Custody',
        'Other'
    ];

    let d = new frappe.ui.Dialog({
        title: __('Create Movement'),
        fields: [
            {
                fieldname: 'movement_type',
                label: __('Movement Type'),
                fieldtype: 'Select',
                options: movement_types.join('\n'),
                reqd: 1,
                default: 'NRM - Customer Movement'
            },
            {
                fieldname: 'date',
                label: __('Date'),
                fieldtype: 'Date',
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                fieldname: 'notes',
                label: __('Notes'),
                fieldtype: 'Small Text'
            }
        ],
        primary_action_label: __('Create'),
        primary_action: function(values) {
            frappe.call({
                method: 'right_hire.api.movements.create_movement_from_agreement',
                args: {
                    agreement_type: agreement_type,
                    agreement_name: frm.doc.name,
                    movement_type: values.movement_type,
                    date: values.date,
                    notes: values.notes
                },
                callback: function(r) {
                    if (r.message && r.message.name) {
                        d.hide();
                        frappe.show_alert({
                            message: __('Movement {0} created', [r.message.name]),
                            indicator: 'green'
                        });
                        frappe.set_route('Form', 'Movements', r.message.name);
                    }
                }
            });
        }
    });
    d.show();
}

// Vehicle Replacement Dialog - handles IN then OUT flow
function show_replacement_dialog(frm, agreement_type) {
    let d = new frappe.ui.Dialog({
        title: __('Vehicle Replacement'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'info',
                options: '<p class="text-muted"><strong>Replacement Flow:</strong><br>1. Current vehicle will be taken IN<br>2. Replacement vehicle will go OUT</p>'
            },
            {
                fieldname: 'section_in',
                fieldtype: 'Section Break',
                label: __('Step 1: Return Current Vehicle')
            },
            {
                fieldname: 'in_mileage',
                label: __('Current Vehicle Mileage'),
                fieldtype: 'Int',
                reqd: 1
            },
            {
                fieldname: 'in_fuel_percentage',
                label: __('Current Vehicle Fuel (%)'),
                fieldtype: 'Int',
                default: 50
            },
            {
                fieldname: 'in_notes',
                label: __('Return Notes'),
                fieldtype: 'Small Text'
            },
            {
                fieldname: 'section_out',
                fieldtype: 'Section Break',
                label: __('Step 2: Issue Replacement Vehicle')
            },
            {
                fieldname: 'replacement_vehicle',
                label: __('Replacement Vehicle'),
                fieldtype: 'Link',
                options: 'Vehicle',
                reqd: 1,
                get_query: function() {
                    return {
                        filters: {
                            'status': 'Available'
                        }
                    };
                }
            },
            {
                fieldname: 'out_mileage',
                label: __('Replacement Vehicle Mileage'),
                fieldtype: 'Int',
                reqd: 1
            },
            {
                fieldname: 'out_fuel_percentage',
                label: __('Replacement Vehicle Fuel (%)'),
                fieldtype: 'Int',
                default: 50
            },
            {
                fieldname: 'out_notes',
                label: __('Handover Notes'),
                fieldtype: 'Small Text'
            },
            {
                fieldname: 'section_reason',
                fieldtype: 'Section Break',
                label: __('Reason')
            },
            {
                fieldname: 'reason',
                label: __('Replacement Reason'),
                fieldtype: 'Small Text',
                reqd: 1
            }
        ],
        size: 'large',
        primary_action_label: __('Process Replacement'),
        primary_action: function(values) {
            frappe.call({
                method: 'right_hire.api.movements.process_vehicle_replacement',
                args: {
                    agreement_type: agreement_type,
                    agreement_name: frm.doc.name,
                    current_vehicle: frm.doc.vehicle,
                    replacement_vehicle: values.replacement_vehicle,
                    in_mileage: values.in_mileage,
                    in_fuel_percentage: values.in_fuel_percentage,
                    in_notes: values.in_notes,
                    out_mileage: values.out_mileage,
                    out_fuel_percentage: values.out_fuel_percentage,
                    out_notes: values.out_notes,
                    reason: values.reason
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        d.hide();
                        frappe.show_alert({
                            message: __('Vehicle replacement processed successfully'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.show();
}
