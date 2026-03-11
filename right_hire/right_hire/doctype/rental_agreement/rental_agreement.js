frappe.ui.form.on('Rental Agreement', {
    customer: function(frm) {
        if (!frm.doc.customer) {
            return;
        }

        // Fetch customer details
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Customer',
                name: frm.doc.customer
            },
            callback: function(r) {
                if (r.message) {
                    const customer = r.message;
                    frm.set_value('customer_name', customer.customer_name);

                    // If customer is a Company, fetch primary contact details
                    if (customer.customer_type === 'Company') {
                        frappe.call({
                            method: 'frappe.client.get_list',
                            args: {
                                doctype: 'Dynamic Link',
                                filters: {
                                    'link_doctype': 'Customer',
                                    'link_name': frm.doc.customer,
                                    'parenttype': 'Contact'
                                },
                                fields: ['parent']
                            },
                            callback: function(r) {
                                if (r.message && r.message.length > 0) {
                                    // Get the first (primary) contact
                                    frappe.call({
                                        method: 'frappe.client.get',
                                        args: {
                                            doctype: 'Contact',
                                            name: r.message[0].parent
                                        },
                                        callback: function(r) {
                                            if (r.message) {
                                                const contact = r.message;
                                                // Set mobile from contact
                                                if (contact.mobile_no) {
                                                    frm.set_value('customer_mobile', contact.mobile_no);
                                                } else if (contact.phone) {
                                                    frm.set_value('customer_mobile', contact.phone);
                                                }
                                            }
                                        }
                                    });
                                }
                            }
                        });
                    }
                    // For Individual customers, leave fields for manual entry
                }
            }
        });
    },

    refresh: function(frm) {
        // Render movement logs panel
        if (!frm.is_new()) {
            render_rental_movement_panel(frm);
            render_rental_fines_tolls_panel(frm);
        }

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

                // Add Create Movement button
                frm.add_custom_button(__('Create Movement'), function() {
                    show_create_movement_dialog(frm);
                }, __('Actions'));

                // Add Vehicle Replacement button
                frm.add_custom_button(__('Vehicle Replacement'), function() {
                    show_replacement_dialog(frm);
                }, __('Actions'));
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
                    if (r.message) {
                        if (r.message.success) {
                            frappe.msgprint(__('Rental started successfully'));
                            frm.reload_doc();
                            d.hide();
                        } else if (r.message.error) {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message.error,
                                indicator: 'red'
                            });
                        }
                    }
                },
                error: function(r) {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Failed to start rental. Please check the error log.'),
                        indicator: 'red'
                    });
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
                    if (r.message) {
                        if (r.message.success) {
                            const formatted = (typeof format_currency === 'function')
                                ? format_currency(r.message.outstanding)
                                : frappe.format(r.message.outstanding, { fieldtype: 'Currency' });
                            frappe.msgprint(__('Vehicle returned successfully. Outstanding amount: {0}', [formatted]));
                            frm.reload_doc();
                            d.hide();
                        } else if (r.message.error) {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message.error,
                                indicator: 'red'
                            });
                        }
                    }
                },
                error: function(r) {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Failed to return vehicle. Please check the error log.'),
                        indicator: 'red'
                    });
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

// Create Movement Dialog
function show_create_movement_dialog(frm) {
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
                    agreement_type: 'Rental Agreement',
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

// Vehicle Replacement Dialog
function show_replacement_dialog(frm) {
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
                    agreement_type: 'Rental Agreement',
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

// Movement logs panel for rental agreements - Apple-like design
function render_rental_movement_panel(frm) {
    // Reuse same CSS as lease agreement
    if (!document.getElementById('agreement-movement-logs-styles')) {
        $(`<style id="agreement-movement-logs-styles">
            .agreement-logs-container { display: flex; gap: 24px; min-height: 300px; }
            .agreement-movements-list { flex: 1; min-width: 0; }
            .agreement-timeline { width: 260px; flex-shrink: 0; max-height: 400px; overflow-y: auto; padding-left: 24px; border-left: 1px solid rgba(0,0,0,0.06); }
            .agreement-timeline::-webkit-scrollbar { width: 4px; }
            .agreement-timeline::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 2px; }
            .agr-tl-header { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 16px; }
            .agr-tl-item { position: relative; padding-left: 20px; padding-bottom: 20px; }
            .agr-tl-item:last-child { padding-bottom: 0; }
            .agr-tl-item::before { content: ''; position: absolute; left: 0; top: 6px; width: 8px; height: 8px; border-radius: 50%; background: #d1d5db; }
            .agr-tl-item::after { content: ''; position: absolute; left: 3.5px; top: 18px; width: 1px; height: calc(100% - 12px); background: #e5e7eb; }
            .agr-tl-item:last-child::after { display: none; }
            .agr-tl-item.color-green::before { background: #22c55e; }
            .agr-tl-item.color-blue::before { background: #3b82f6; }
            .agr-tl-item.color-orange::before { background: #f97316; }
            .agr-tl-item.color-red::before { background: #ef4444; }
            .agr-tl-item.color-purple::before { background: #a855f7; }
            .agr-tl-item.color-yellow::before { background: #eab308; }
            .agr-tl-item.color-gray::before { background: #9ca3af; }
            .agr-tl-title { font-size: 13px; font-weight: 500; color: var(--text-color); line-height: 1.3; }
            .agr-tl-title a { color: inherit; text-decoration: none; }
            .agr-tl-title a:hover { color: var(--primary); }
            .agr-tl-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
            .agr-tl-date { font-size: 11px; color: var(--text-light); margin-top: 4px; }
            @media (max-width: 768px) {
                .agreement-logs-container { flex-direction: column; }
                .agreement-timeline { width: 100%; max-height: 250px; border-left: none; border-top: 1px solid rgba(0,0,0,0.06); padding-left: 0; padding-top: 16px; }
            }
        </style>`).appendTo('head');
    }

    const htmlContent = `
        <div class="agreement-logs-container">
            <div class="agreement-movements-list">
                <div id="rental_movements_table"><div class="text-muted">Loading...</div></div>
                <div class="flex items-center justify-between" style="margin-top:8px;">
                    <div class="text-muted small" id="rental_mov_count"></div>
                    <div class="btn-group">
                        <button class="btn btn-xs btn-default" id="rental_mov_prev">Prev</button>
                        <button class="btn btn-xs btn-default" id="rental_mov_next">Next</button>
                    </div>
                </div>
            </div>
            <div class="agreement-timeline">
                <div class="agr-tl-header">Timeline</div>
                <div id="rental_timeline"><div class="text-muted small">Loading...</div></div>
            </div>
        </div>
    `;

    frm.set_df_property('movement_logs_html', 'options', htmlContent);
    frm.refresh_field('movement_logs_html');

    setTimeout(() => {
        let page = 1;
        const page_len = 10;

        async function loadMovements() {
            const { message } = await frappe.call({
                method: 'right_hire.api.movements.get_agreement_movements',
                args: { agreement_type: 'Rental Agreement', agreement_no: frm.doc.name, page, page_len },
                freeze: false
            });
            const rows = message?.data || [];
            const total = message?.total || 0;
            $('#rental_mov_count').text(total ? `${total} movement(s)` : 'No movements');
            const html = rows.length ? `
                <table class="table table-bordered table-sm" style="font-size: 12px;">
                    <thead><tr><th>Out Date/Time</th><th>In Date/Time</th><th>ID</th><th>Type</th><th>Status</th><th>Vehicle</th></tr></thead>
                    <tbody>
                        ${rows.map(r => {
                            const outDt = r.out_date_time ? frappe.datetime.str_to_user(r.out_date_time.substring(0, 16)) : '-';
                            const inDt = r.in_date_time ? frappe.datetime.str_to_user(r.in_date_time.substring(0, 16)) : '-';
                            return `
                            <tr>
                                <td style="white-space:nowrap;">${outDt}</td>
                                <td style="white-space:nowrap;">${inDt}</td>
                                <td><a href="/app/movements/${r.name}">${r.name}</a></td>
                                <td>${frappe.utils.escape_html(r.movement_type || '')}</td>
                                <td><span class="indicator-pill ${r.status === 'Returned' ? 'green' : r.status === 'Out Only' ? 'blue' : 'gray'}">${r.status || ''}</span></td>
                                <td><a href="/app/vehicle/${r.vehicle}">${r.vehicle || ''}</a></td>
                            </tr>
                        `}).join('')}
                    </tbody>
                </table>
            ` : '<div class="text-muted text-center py-3">No movements yet</div>';
            $('#rental_movements_table').html(html);
            const max_page = Math.max(1, Math.ceil(total / page_len));
            $('#rental_mov_prev').prop('disabled', page <= 1);
            $('#rental_mov_next').prop('disabled', page >= max_page);
        }

        async function loadTimeline() {
            const { message } = await frappe.call({
                method: 'right_hire.api.movements.get_agreement_timeline',
                args: { agreement_type: 'Rental Agreement', agreement_no: frm.doc.name },
                freeze: false
            });
            const events = message || [];
            if (!events.length) {
                $('#rental_timeline').html('<div class="text-muted small">No events</div>');
                return;
            }
            const html = events.map(e => `
                <div class="agr-tl-item color-${e.color || 'gray'}">
                    <div class="agr-tl-title">
                        ${e.link ? `<a href="${e.link}">${frappe.utils.escape_html(e.title)}</a>` : frappe.utils.escape_html(e.title)}
                    </div>
                    ${e.subtitle ? `<div class="agr-tl-subtitle">${frappe.utils.escape_html(e.subtitle)}</div>` : ''}
                    <div class="agr-tl-date">${frappe.datetime.str_to_user(e.date) || e.date}</div>
                </div>
            `).join('');
            $('#rental_timeline').html(html);
        }

        $('#rental_mov_prev').off('click').on('click', () => { if (page > 1) { page--; loadMovements(); } });
        $('#rental_mov_next').off('click').on('click', () => { page++; loadMovements(); });

        loadMovements();
        loadTimeline();
    }, 100);
}

// Fines & Tolls panel for rental agreements
function render_rental_fines_tolls_panel(frm) {
    if (!document.getElementById('rental-ft-styles')) {
        $(`<style id="rental-ft-styles">
            .rental-ft-container { min-height: 300px; }
            .rental-ft-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-color); margin-bottom: 16px; }
            .rental-ft-tab { padding: 10px 20px; font-size: 13px; font-weight: 500; color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.2s; }
            .rental-ft-tab:hover { color: var(--text-color); }
            .rental-ft-tab.active { color: var(--primary); border-bottom-color: var(--primary); }
            .rental-ft-tab-content { display: none; }
            .rental-ft-tab-content.active { display: block; }
            .rental-ft-summary { display: flex; gap: 20px; margin-bottom: 16px; flex-wrap: wrap; }
            .rental-ft-summary-card { background: var(--fg-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px 16px; min-width: 100px; }
            .rental-ft-summary-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 4px; }
            .rental-ft-summary-value { font-size: 18px; font-weight: 600; color: var(--text-color); }
            .rental-ft-summary-count { font-size: 11px; color: var(--text-muted); }
            .rental-ft-table { font-size: 12px; }
            .rental-ft-table th { font-weight: 600; background: var(--bg-color); }
            .rental-ft-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; }
            .rental-ft-badge.salik { background: #dbeafe; color: #1d4ed8; }
            .rental-ft-badge.darb { background: #fef3c7; color: #b45309; }
            .rental-ft-badge.fine { background: #fee2e2; color: #b91c1c; }
            .rental-ft-badge.paid { background: #dcfce7; color: #166534; }
            .rental-ft-badge.unpaid { background: #fef9c3; color: #854d0e; }
            .rental-ft-badge.charged { background: #e9d5ff; color: #7c3aed; }
        </style>`).appendTo('head');
    }

    const htmlContent = `
        <div class="rental-ft-container">
            <div class="rental-ft-tabs">
                <div class="rental-ft-tab active" data-tab="all">All</div>
                <div class="rental-ft-tab" data-tab="salik">Salik</div>
                <div class="rental-ft-tab" data-tab="darb">Darb</div>
                <div class="rental-ft-tab" data-tab="fines">Traffic Fines</div>
            </div>
            <div>
                <div class="rental-ft-tab-content active" id="rental-ft-tab-all"><div class="text-muted">Loading...</div></div>
                <div class="rental-ft-tab-content" id="rental-ft-tab-salik"></div>
                <div class="rental-ft-tab-content" id="rental-ft-tab-darb"></div>
                <div class="rental-ft-tab-content" id="rental-ft-tab-fines"></div>
            </div>
        </div>
    `;

    frm.set_df_property('fines_tolls_html', 'options', htmlContent);
    frm.refresh_field('fines_tolls_html');

    setTimeout(() => {
        $('.rental-ft-tab').off('click').on('click', function() {
            const tab = $(this).data('tab');
            $('.rental-ft-tab').removeClass('active');
            $(this).addClass('active');
            $('.rental-ft-tab-content').removeClass('active');
            $(`#rental-ft-tab-${tab}`).addClass('active');
        });

        loadRentalFinesTolls(frm);
    }, 100);
}

async function loadRentalFinesTolls(frm) {
    const { message } = await frappe.call({
        method: 'right_hire.api.fines_tolls.get_agreement_fines_tolls',
        args: { agreement_type: 'Rental Agreement', agreement_no: frm.doc.name, page: 1, page_len: 100 },
        freeze: false
    });

    const items = message?.data || [];
    const summary = message?.summary || {};

    const salik = items.filter(i => i.type === 'Salik');
    const darb = items.filter(i => i.type === 'Darb');
    const fines = items.filter(i => i.type === 'Traffic Fine');

    const allHtml = `
        <div class="rental-ft-summary">
            <div class="rental-ft-summary-card">
                <div class="rental-ft-summary-label">Total</div>
                <div class="rental-ft-summary-value">AED ${formatRentalCurrency(summary.grand_total || 0)}</div>
                <div class="rental-ft-summary-count">${items.length} records</div>
            </div>
            <div class="rental-ft-summary-card">
                <div class="rental-ft-summary-label">Salik</div>
                <div class="rental-ft-summary-value">AED ${formatRentalCurrency(summary.salik_total || 0)}</div>
                <div class="rental-ft-summary-count">${summary.salik_count || 0} trips</div>
            </div>
            <div class="rental-ft-summary-card">
                <div class="rental-ft-summary-label">Darb</div>
                <div class="rental-ft-summary-value">AED ${formatRentalCurrency(summary.darb_total || 0)}</div>
                <div class="rental-ft-summary-count">${summary.darb_count || 0} trips</div>
            </div>
            <div class="rental-ft-summary-card">
                <div class="rental-ft-summary-label">Traffic Fines</div>
                <div class="rental-ft-summary-value">AED ${formatRentalCurrency(summary.fines_total || 0)}</div>
                <div class="rental-ft-summary-count">${summary.fines_count || 0} fines</div>
            </div>
        </div>
        ${renderRentalFinesTollsTable(items)}
    `;
    $('#rental-ft-tab-all').html(allHtml);
    $('#rental-ft-tab-salik').html(renderRentalFinesTollsTable(salik, 'Salik'));
    $('#rental-ft-tab-darb').html(renderRentalFinesTollsTable(darb, 'Darb'));
    $('#rental-ft-tab-fines').html(renderRentalFinesTollsTable(fines, 'Traffic Fine'));
}

function renderRentalFinesTollsTable(items, type = null) {
    if (!items.length) {
        return `<div class="text-muted text-center py-4">No ${type || 'fines or tolls'} found</div>`;
    }

    return `
        <div class="table-responsive">
            <table class="table table-bordered table-sm table-hover rental-ft-table">
                <thead>
                    <tr>
                        <th>Date/Time</th>
                        ${!type ? '<th>Type</th>' : ''}
                        <th>Vehicle</th>
                        <th>Location</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Charged</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(item => {
                        const dateStr = frappe.datetime.str_to_user(item.date) || item.date || '-';
                        const timeStr = item.time ? item.time.substring(0, 5) : '';
                        const dateTimeStr = timeStr ? `${dateStr} ${timeStr}` : dateStr;
                        return `
                        <tr>
                            <td style="white-space:nowrap;">${dateTimeStr}</td>
                            ${!type ? `<td><span class="rental-ft-badge ${item.type.toLowerCase().replace(' ', '')}">${item.type}</span></td>` : ''}
                            <td><a href="/app/vehicle/${item.vehicle}">${item.vehicle || '-'}</a></td>
                            <td>${frappe.utils.escape_html(item.location || item.details || '-')}</td>
                            <td style="text-align:right; font-weight:500;">AED ${formatRentalCurrency(item.amount || 0)}</td>
                            <td><span class="rental-ft-badge ${item.status === 'Paid' ? 'paid' : 'unpaid'}">${item.status || 'Unpaid'}</span></td>
                            <td>${item.charged_to_customer ? '<span class="rental-ft-badge charged">Charged</span>' : '-'}</td>
                            <td><a href="/app/${item.doctype.toLowerCase().replace(/ /g, '-')}/${item.name}" class="btn btn-xs btn-default">View</a></td>
                        </tr>
                    `}).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function formatRentalCurrency(value) {
    return (value || 0).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}
