frappe.ui.form.on('Customer', {

    refresh: function(frm) {
        if (!frm.is_new()) {
            // Add Create Movement button
            frm.add_custom_button(__('Create Movement'), function() {
                show_customer_movement_dialog(frm);
            }, __('Actions'));

            // Add Vehicle Replacement button
            frm.add_custom_button(__('Vehicle Replacement'), function() {
                show_customer_replacement_dialog(frm);
            }, __('Actions'));
        }
    },

    // ==================== KYC DOCUMENT SCAN BUTTONS ====================

    scan_passport_btn: function(frm) {
        if (!frm.doc.attach_passport) {
            frappe.msgprint(__('Please upload passport file first'));
            return;
        }
        scan_document(frm, 'passport', frm.doc.attach_passport, {
            number_field: 'passport_number',
            expiry_field: 'passport_expiry'
        });
    },

    scan_license_btn: function(frm) {
        if (!frm.doc.attach_license) {
            frappe.msgprint(__('Please upload driving license file first'));
            return;
        }
        scan_document(frm, 'license', frm.doc.attach_license, {
            number_field: 'license_number',
            expiry_field: 'license_expiry'
        });
    },

    scan_id_btn: function(frm) {
        if (!frm.doc.attach_id) {
            frappe.msgprint(__('Please upload national ID file first'));
            return;
        }
        scan_document(frm, 'id', frm.doc.attach_id, {
            number_field: 'id_number',
            expiry_field: 'id_expiry'
        });
    },

    // ==================== COMPANY DOCUMENT SCAN BUTTONS ====================

    scan_credit_application_btn: function(frm) {
        if (!frm.doc.credit_application_file) {
            frappe.msgprint(__('Please upload credit application file first'));
            return;
        }
        scan_company_document(frm, 'credit_application', frm.doc.credit_application_file, {
            number_field: 'credit_application_number',
            expiry_field: 'credit_application_expiry',
            extra_fields: ['credit_limit_approved']
        });
    },

    scan_trn_certificate_btn: function(frm) {
        if (!frm.doc.trn_certificate_file) {
            frappe.msgprint(__('Please upload TRN certificate file first'));
            return;
        }
        scan_company_document(frm, 'trn_certificate', frm.doc.trn_certificate_file, {
            number_field: 'trn_number',
            expiry_field: 'trn_certificate_expiry'
        });
    },

    scan_trade_license_btn: function(frm) {
        if (!frm.doc.trade_license_file) {
            frappe.msgprint(__('Please upload trade license file first'));
            return;
        }
        scan_company_document(frm, 'trade_license', frm.doc.trade_license_file, {
            number_field: 'trade_license_number',
            expiry_field: 'trade_license_expiry'
        });
    },

    // ==================== PORTAL ACCOUNT BUTTONS ====================

    set_portal_password_btn: function(frm) {
        let d = new frappe.ui.Dialog({
            title: __('Set Portal Password'),
            fields: [
                {
                    fieldname: 'new_password',
                    label: __('New Password'),
                    fieldtype: 'Password',
                    reqd: 1
                },
                {
                    fieldname: 'confirm_password',
                    label: __('Confirm Password'),
                    fieldtype: 'Password',
                    reqd: 1
                }
            ],
            primary_action_label: __('Set Password'),
            primary_action: function(values) {
                if (values.new_password !== values.confirm_password) {
                    frappe.msgprint(__('Passwords do not match'));
                    return;
                }
                frappe.call({
                    method: 'right_hire.right_hire.doctype.customer.customer.set_portal_password',
                    args: {
                        customer: frm.doc.name,
                        new_password: values.new_password
                    },
                    callback: function(r) {
                        d.hide();
                    }
                });
            }
        });
        d.show();
    },

    create_portal_user_btn: function(frm) {
        frappe.confirm(
            __('Create a portal user for {0} ({1})?', [frm.doc.customer_name, frm.doc.email]),
            function() {
                frappe.call({
                    method: 'right_hire.right_hire.doctype.customer.customer.create_portal_user_for_customer',
                    args: { customer: frm.doc.name },
                    callback: function(r) {
                        frm.reload_doc();
                    }
                });
            }
        );
    },

    // ==================== AUTO-UPDATE STATUS ====================

    credit_application_expiry: function(frm) {
        update_company_documents_status(frm);
    },

    trn_certificate_expiry: function(frm) {
        update_company_documents_status(frm);
    },

    trade_license_expiry: function(frm) {
        update_company_documents_status(frm);
    }
});


// ==================== HELPER FUNCTIONS ====================

function scan_document(frm, doc_type, file_url, field_mapping) {
    frappe.show_alert({
        message: __('Scanning document with Azure Document Intelligence...'),
        indicator: 'blue'
    }, 3);

    frappe.call({
        method: 'right_hire.right_hire.azure_di.analyze_scan',
        args: {
            file_url: file_url,
            use_urlsource: 0,
            debug: 0
        },
        callback: function(r) {
            if (r.message && r.message.fields) {
                const fields = r.message.fields;

                // Map fields
                if (fields[field_mapping.number_field]) {
                    frm.set_value(field_mapping.number_field, fields[field_mapping.number_field]);
                }
                if (fields[field_mapping.expiry_field]) {
                    frm.set_value(field_mapping.expiry_field, fields[field_mapping.expiry_field]);
                }

                // Additional fields for specific document types
                if (fields.date_of_birth) {
                    frm.set_value('date_of_birth', fields.date_of_birth);
                }
                if (fields.customer_name && !frm.doc.customer_name) {
                    frm.set_value('customer_name', fields.customer_name);
                }

                frappe.show_alert({
                    message: __('Document scanned successfully'),
                    indicator: 'green'
                }, 3);
            } else {
                frappe.msgprint(__('No data extracted from document'));
            }
        },
        error: function(r) {
            frappe.msgprint(__('Failed to scan document. Please check Azure configuration.'));
        }
    });
}


function scan_company_document(frm, doc_type, file_url, field_mapping) {
    frappe.show_alert({
        message: __('Scanning document with Azure Document Intelligence...'),
        indicator: 'blue'
    }, 3);

    const method_map = {
        'credit_application': 'right_hire.right_hire.azure_di.scan_credit_application',
        'trn_certificate': 'right_hire.right_hire.azure_di.scan_trn_certificate',
        'trade_license': 'right_hire.right_hire.azure_di.scan_trade_license'
    };

    frappe.call({
        method: method_map[doc_type],
        args: {
            file_url: file_url,
            use_urlsource: 0,
            debug: 0
        },
        callback: function(r) {
            if (r.message && r.message.fields) {
                const fields = r.message.fields;

                // Map standard fields
                if (fields[field_mapping.number_field]) {
                    frm.set_value(field_mapping.number_field, fields[field_mapping.number_field]);
                }
                if (fields[field_mapping.expiry_field]) {
                    frm.set_value(field_mapping.expiry_field, fields[field_mapping.expiry_field]);
                }

                // Map extra fields (e.g., credit_limit_approved)
                if (field_mapping.extra_fields) {
                    field_mapping.extra_fields.forEach(function(field) {
                        if (fields[field]) {
                            frm.set_value(field, fields[field]);
                        }
                    });
                }

                // Update last scanned timestamp
                frm.set_value('last_scanned_date', frappe.datetime.now_datetime());

                // Update overall status
                update_company_documents_status(frm);

                frappe.show_alert({
                    message: __('Document scanned successfully'),
                    indicator: 'green'
                }, 3);
            } else {
                frappe.msgprint(__('No data extracted from document'));
            }
        },
        error: function(r) {
            frappe.msgprint(__('Failed to scan document. Please check Azure configuration.'));
        }
    });
}


function update_company_documents_status(frm) {
    // Only calculate status for Company type customers
    if (frm.doc.customer_type !== 'Company') {
        frm.set_value('company_documents_status', 'Not Applicable');
        return;
    }

    const today = frappe.datetime.get_today();
    const thirty_days_ahead = frappe.datetime.add_days(today, 30);

    const docs = [
        {
            file: frm.doc.credit_application_file,
            number: frm.doc.credit_application_number,
            expiry: frm.doc.credit_application_expiry,
            name: 'Credit Application'
        },
        {
            file: frm.doc.trn_certificate_file,
            number: frm.doc.trn_number,
            expiry: frm.doc.trn_certificate_expiry,
            name: 'TRN Certificate'
        },
        {
            file: frm.doc.trade_license_file,
            number: frm.doc.trade_license_number,
            expiry: frm.doc.trade_license_expiry,
            name: 'Trade License'
        }
    ];

    let has_expired = false;
    let has_expiring_soon = false;
    let has_missing = false;

    docs.forEach(function(doc) {
        // Check if document is missing
        if (!doc.file || !doc.number) {
            has_missing = true;
            return;
        }

        // Check expiry status
        if (doc.expiry) {
            if (doc.expiry < today) {
                has_expired = true;
            } else if (doc.expiry <= thirty_days_ahead) {
                has_expiring_soon = true;
            }
        }
    });

    // Determine overall status
    let status = 'All Valid';
    if (has_expired) {
        status = 'Expired';
    } else if (has_missing) {
        status = 'Missing Documents';
    } else if (has_expiring_soon) {
        status = 'Expiring Soon';
    }

    frm.set_value('company_documents_status', status);
}


// ==================== MOVEMENT DIALOGS ====================

function show_customer_movement_dialog(frm) {
    // First, get customer's active vehicles
    frappe.call({
        method: 'right_hire.api.movements.get_customer_active_vehicles',
        args: {
            customer_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let vehicles = r.message;
                let vehicle_options = vehicles.map(v => v.vehicle).join('\n');

                let movement_types = [
                    'NRM - Customer Movement',
                    'Delivery',
                    'Recovery',
                    'Workshop',
                    'Custody',
                    'Other'
                ];

                let d = new frappe.ui.Dialog({
                    title: __('Create Movement for Customer'),
                    fields: [
                        {
                            fieldname: 'vehicle',
                            label: __('Vehicle'),
                            fieldtype: 'Select',
                            options: vehicle_options,
                            reqd: 1
                        },
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
                            method: 'right_hire.api.movements.create_movement_from_customer',
                            args: {
                                customer_name: frm.doc.name,
                                vehicle: values.vehicle,
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
            } else {
                frappe.msgprint(__('No active vehicles found for this customer. Please ensure the customer has an active Rental Agreement, Lease Agreement, or Lease to Own.'));
            }
        }
    });
}

function show_customer_replacement_dialog(frm) {
    // First, get customer's active vehicles
    frappe.call({
        method: 'right_hire.api.movements.get_customer_active_vehicles',
        args: {
            customer_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let vehicles = r.message;
                let vehicle_options = vehicles.map(v => ({
                    label: v.vehicle + ' (' + v.agreement_type + ': ' + v.agreement_name + ')',
                    value: JSON.stringify(v)
                }));

                let d = new frappe.ui.Dialog({
                    title: __('Vehicle Replacement'),
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'info',
                            options: '<p class="text-muted"><strong>Replacement Flow:</strong><br>1. Current vehicle will be taken IN<br>2. Replacement vehicle will go OUT</p>'
                        },
                        {
                            fieldname: 'current_vehicle_info',
                            label: __('Current Vehicle'),
                            fieldtype: 'Select',
                            options: vehicle_options.map(v => v.label).join('\n'),
                            reqd: 1
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
                        // Find the selected vehicle info
                        let selected_label = values.current_vehicle_info;
                        let selected_vehicle = vehicles.find(v =>
                            selected_label.startsWith(v.vehicle + ' ('));

                        if (!selected_vehicle) {
                            frappe.msgprint(__('Please select a valid vehicle'));
                            return;
                        }

                        frappe.call({
                            method: 'right_hire.api.movements.process_vehicle_replacement',
                            args: {
                                agreement_type: selected_vehicle.agreement_type,
                                agreement_name: selected_vehicle.agreement_name,
                                current_vehicle: selected_vehicle.vehicle,
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
            } else {
                frappe.msgprint(__('No active vehicles found for this customer. Please ensure the customer has an active Rental Agreement, Lease Agreement, or Lease to Own.'));
            }
        }
    });
}
