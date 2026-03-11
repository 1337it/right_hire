// Copyright (c) 2026, Right Hire and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lease Agreement', {
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
								fields: ['parent'],
								limit_page_length: 1
							},
							callback: function(r) {
								if (r.message && r.message.length > 0) {
									// Get the primary contact
									frappe.call({
										method: 'frappe.client.get',
										args: {
											doctype: 'Contact',
											name: r.message[0].parent
										},
										callback: function(r) {
											if (r.message) {
												const contact = r.message;
												// Set contact details
												const fullName = [contact.first_name, contact.last_name].filter(Boolean).join(' ');
												if (fullName) {
													frm.set_value('contact_person', fullName);
												}
												if (contact.mobile_no) {
													frm.set_value('contact_mobile', contact.mobile_no);
												} else if (contact.phone) {
													frm.set_value('contact_mobile', contact.phone);
												}
												if (contact.email_id) {
													frm.set_value('contact_email', contact.email_id);
												}
											}
										}
									});
								}
							}
						});

						// Also fetch primary address
						frappe.call({
							method: 'frappe.client.get_list',
							args: {
								doctype: 'Dynamic Link',
								filters: {
									'link_doctype': 'Customer',
									'link_name': frm.doc.customer,
									'parenttype': 'Address'
								},
								fields: ['parent'],
								limit_page_length: 1
							},
							callback: function(r) {
								if (r.message && r.message.length > 0) {
									frappe.call({
										method: 'frappe.client.get',
										args: {
											doctype: 'Address',
											name: r.message[0].parent
										},
										callback: function(r) {
											if (r.message) {
												const addr = r.message;
												const addressParts = [
													addr.address_line1,
													addr.address_line2,
													addr.city,
													addr.state,
													addr.country
												].filter(Boolean);
												if (addressParts.length > 0) {
													frm.set_value('customer_address', addressParts.join(', '));
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
		// Make lease_status read-only when document is draft
		if (frm.doc.docstatus === 0) {
			frm.set_df_property('lease_status', 'read_only', 1);
		}

		// Render movement logs panel
		if (!frm.is_new()) {
			render_agreement_movement_panel(frm, 'Lease Agreement');
			render_agreement_fines_tolls_panel(frm, 'Lease Agreement');
		}

		// Generate Schedule button for Draft agreements
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Generate Invoice Schedule'), function() {
				// Validate required fields
				if (!frm.doc.start_date) {
					frappe.msgprint(__('Please set Start Date first'));
					return;
				}
				if (!frm.doc.tenure_months || frm.doc.tenure_months <= 0) {
					frappe.msgprint(__('Please set Tenure (Months) first'));
					return;
				}
				if (!frm.doc.billing_cycle) {
					frappe.msgprint(__('Please set Billing Cycle first'));
					return;
				}
				if (!frm.doc.monthly_rate || frm.doc.monthly_rate <= 0) {
					frappe.msgprint(__('Please set Monthly Rate first'));
					return;
				}

				frappe.call({
					method: 'right_hire.right_hire.doctype.lease_agreement.lease_agreement.generate_schedule',
					args: {
						lease_agreement: frm.doc.name
					},
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __('Invoice schedule generated with {0} entries', [r.message.count]),
								indicator: 'green'
							});
							frm.reload_doc();
						}
					}
				});
			}).addClass('btn-primary');
		}

		if (!frm.is_new() && frm.doc.lease_status === 'Active') {
			// Add Generate Invoices button - always visible for active leases
			frm.add_custom_button(__('Generate Invoices'), function() {
				frappe.call({
					method: 'right_hire.right_hire.doctype.lease_agreement.lease_agreement.generate_invoices_for_agreement',
					args: {
						lease_agreement: frm.doc.name
					},
					freeze: true,
					freeze_message: __('Generating invoices...'),
					callback: function(r) {
						if (r.message) {
							if (r.message.created && r.message.created.length > 0) {
								frappe.show_alert({
									message: __('Created {0} invoice(s): {1}', [r.message.created.length, r.message.created.join(', ')]),
									indicator: 'green'
								});
								frm.reload_doc();
							} else {
								frappe.show_alert({
									message: __('No pending invoices to generate'),
									indicator: 'blue'
								});
							}
						}
					}
				});
			}).addClass('btn-primary');

			// Add Create Movement button for active lease agreements
			frm.add_custom_button(__('Create Movement'), function() {
				show_lease_movement_dialog(frm);
			}, __('Actions'));

			// Add Vehicle Replacement button
			frm.add_custom_button(__('Vehicle Replacement'), function() {
				show_lease_replacement_dialog(frm);
			}, __('Actions'));

			// Add Supplementary Salik Invoice button
			frm.add_custom_button(__('Salik Supplementary Invoice'), function() {
				frappe.call({
					method: 'right_hire.right_hire.doctype.lease_agreement.lease_agreement.create_salik_supplementary_invoice',
					args: {
						lease_agreement: frm.doc.name
					},
					freeze: true,
					freeze_message: __('Creating Salik invoice...'),
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({
								message: __('Supplementary invoice {0} created', [r.message]),
								indicator: 'green'
							});
							frappe.set_route('Form', 'Sales Invoice', r.message);
						}
					}
				});
			}, __('Actions'));
		}
	},

	terms_template: function(frm) {
		// When terms template is selected, fetch and populate terms_and_conditions
		if (frm.doc.terms_template) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Terms and Conditions',
					name: frm.doc.terms_template
				},
				callback: function(r) {
					if (r.message && r.message.terms) {
						frm.set_value('terms_and_conditions', r.message.terms);
					}
				}
			});
		} else {
			// Template cleared - optionally clear terms
			frm.set_value('terms_and_conditions', '');
		}
	},

	customer: function(frm) {
		// When customer is selected, check type and populate driver details
		if (!frm.doc.customer) {
			// Customer cleared - clear driver fields
			clear_driver_fields(frm);
			return;
		}

		// Fetch customer details including type and driver documents
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Customer',
				name: frm.doc.customer
			},
			callback: function(r) {
				if (r.message) {
					let customer = r.message;

					// Check if customer type is Individual
					if (customer.customer_type === 'Individual') {
						// Check if driving license is uploaded (either attach_license or license data exists)
						let has_license_data = customer.license_no || customer.license_number;

						if (has_license_data) {
							// Populate driver details from customer
							populate_driver_from_customer(frm, customer);
						} else {
							// No license uploaded - show message but don't populate
							frappe.show_alert({
								message: __('Customer has no driving license on file. Driver details will need to be entered manually.'),
								indicator: 'yellow'
							}, 5);
						}
					} else {
						// Company customer - don't populate driver details
						// Clear any auto-populated values and leave for manual entry
						frappe.show_alert({
							message: __('Company customer selected. Driver details should be entered manually.'),
							indicator: 'blue'
						}, 5);
					}
				}
			}
		});
	}
});

function populate_driver_from_customer(frm, customer) {
	// Populate driver name and mobile from customer basic info
	frm.set_value('driver_name', customer.customer_name || '');
	frm.set_value('driver_mobile', customer.mobile || '');

	// EID (Emirates ID) - prefer scanned data (id_number) over manual (id_no)
	let eid_no = customer.id_number || customer.id_no || '';
	let eid_expiry = customer.id_expiry || customer.id_expiry_2 || '';

	frm.set_value('eid_no', eid_no);
	frm.set_value('eid_exp_date', eid_expiry);
	// EID issue date not available in Customer doctype - leave empty

	// Passport - prefer scanned data (passport_number) over manual (passport_no)
	let passport_no = customer.passport_number || customer.passport_no || '';
	let passport_expiry = customer.passport_expiry || customer.passport_expiry_2 || '';

	frm.set_value('passport_number', passport_no);
	frm.set_value('passport_exp_date', passport_expiry);
	// Passport issue date not available in Customer doctype - leave empty

	// Driving License - prefer scanned data (license_number) over manual (license_no)
	let license_no = customer.license_number || customer.license_no || '';
	let license_expiry = customer.license_expiry || customer.license_expiry_2 || '';
	let license_country = customer.license_country || '';

	frm.set_value('driving_license_no', license_no);
	frm.set_value('driving_license_exp_date', license_expiry);
	frm.set_value('license_issued_by', license_country);
	// License issue date not available in Customer doctype - leave empty

	frappe.show_alert({
		message: __('Driver details populated from customer documents'),
		indicator: 'green'
	}, 5);
}

function clear_driver_fields(frm) {
	// Clear all driver fields when customer is removed
	frm.set_value('driver_name', '');
	frm.set_value('driver_mobile', '');
	frm.set_value('eid_no', '');
	frm.set_value('eid_issue_date', '');
	frm.set_value('eid_exp_date', '');
	frm.set_value('passport_number', '');
	frm.set_value('passport_issue_date', '');
	frm.set_value('passport_exp_date', '');
	frm.set_value('driving_license_no', '');
	frm.set_value('license_issued_date', '');
	frm.set_value('license_issued_by', '');
	frm.set_value('driving_license_exp_date', '');
}

// Create Movement Dialog for Lease Agreement
function show_lease_movement_dialog(frm) {
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
					agreement_type: 'Lease Agreement',
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

// Vehicle Replacement Dialog for Lease Agreement
function show_lease_replacement_dialog(frm) {
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
					agreement_type: 'Lease Agreement',
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

// Movement logs panel for agreements - Apple-like design
function render_agreement_movement_panel(frm, agreement_type) {
	// Add CSS
	if (!document.getElementById('agreement-movement-logs-styles')) {
		$(`<style id="agreement-movement-logs-styles">
			.agreement-logs-container { display: flex; gap: 24px; min-height: 300px; }
			.agreement-movements-list { flex: 1; min-width: 0; }
			.agreement-timeline { width: 260px; flex-shrink: 0; max-height: 400px; overflow-y: auto; padding-left: 24px; border-left: 1px solid rgba(0,0,0,0.06); }
			.agr-tl-header { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 16px; }
			.agr-tl-item { position: relative; padding-left: 20px; padding-bottom: 20px; }
			.agr-tl-item:last-child { padding-bottom: 0; }
			.agr-tl-item::before { content: ''; position: absolute; left: 0; top: 6px; width: 8px; height: 8px; border-radius: 50%; background: #d1d5db; }
			.agr-tl-item::after { content: ''; position: absolute; left: 3.5px; top: 18px; width: 1px; height: calc(100% - 12px); background: #e5e7eb; }
			.agr-tl-item:last-child::after { display: none; }
			.agr-tl-item.color-green::before { background: #22c55e; }
			.agr-tl-item.color-blue::before { background: #3b82f6; }
			.agr-tl-item.color-orange::before { background: #f97316; }
			.agr-tl-item.color-purple::before { background: #a855f7; }
			.agr-tl-item.color-gray::before { background: #9ca3af; }
			.agr-tl-title { font-size: 13px; font-weight: 500; color: var(--text-color); }
			.agr-tl-title a { color: inherit; text-decoration: none; }
			.agr-tl-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
			.agr-tl-date { font-size: 11px; color: var(--text-light); margin-top: 4px; }
		</style>`).appendTo('head');
	}

	const htmlContent = `
		<div class="agreement-logs-container">
			<div class="agreement-movements-list">
				<div id="agr_movements_table"><div class="text-muted">Loading...</div></div>
				<div class="flex items-center justify-between" style="margin-top:8px;">
					<div class="text-muted small" id="agr_mov_count"></div>
					<div class="btn-group">
						<button class="btn btn-xs btn-default" id="agr_mov_prev">Prev</button>
						<button class="btn btn-xs btn-default" id="agr_mov_next">Next</button>
					</div>
				</div>
			</div>
			<div class="agreement-timeline">
				<div class="agr-tl-header">Timeline</div>
				<div id="agr_timeline"><div class="text-muted small">Loading...</div></div>
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
				args: { agreement_type: agreement_type, agreement_no: frm.doc.name, page, page_len },
				freeze: false
			});
			const rows = message?.data || [];
			const total = message?.total || 0;
			$('#agr_mov_count').text(total ? `${total} movement(s)` : 'No movements');
			const html = rows.length ? `
				<table class="table table-bordered table-sm" style="font-size: 12px;">
					<thead><tr><th>Out Date/Time</th><th>In Date/Time</th><th>ID</th><th>Type</th><th>Status</th><th>Vehicle</th></tr></thead>
					<tbody>${rows.map(r => {
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
					`}).join('')}</tbody>
				</table>
			` : '<div class="text-muted text-center py-3">No movements yet</div>';
			$('#agr_movements_table').html(html);
			$('#agr_mov_prev').prop('disabled', page <= 1);
			$('#agr_mov_next').prop('disabled', page >= Math.ceil(total / page_len));
		}

		async function loadTimeline() {
			const { message } = await frappe.call({
				method: 'right_hire.api.movements.get_agreement_timeline',
				args: { agreement_type: agreement_type, agreement_no: frm.doc.name },
				freeze: false
			});
			const events = message || [];
			if (!events.length) { $('#agr_timeline').html('<div class="text-muted small">No events</div>'); return; }
			$('#agr_timeline').html(events.map(e => `
				<div class="agr-tl-item color-${e.color || 'gray'}">
					<div class="agr-tl-title">${e.link ? `<a href="${e.link}">${frappe.utils.escape_html(e.title)}</a>` : frappe.utils.escape_html(e.title)}</div>
					${e.subtitle ? `<div class="agr-tl-subtitle">${frappe.utils.escape_html(e.subtitle)}</div>` : ''}
					<div class="agr-tl-date">${frappe.datetime.str_to_user(e.date) || e.date}</div>
				</div>
			`).join(''));
		}

		$('#agr_mov_prev').off('click').on('click', () => { if (page > 1) { page--; loadMovements(); } });
		$('#agr_mov_next').off('click').on('click', () => { page++; loadMovements(); });
		loadMovements();
		loadTimeline();
	}, 100);
}

// Fines & Tolls panel for agreements
function render_agreement_fines_tolls_panel(frm, agreement_type) {
	// Add CSS for fines/tolls panel
	if (!document.getElementById('agr-fines-tolls-styles')) {
		$(`<style id="agr-fines-tolls-styles">
			.agr-ft-container { min-height: 300px; }
			.agr-ft-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-color); margin-bottom: 16px; }
			.agr-ft-tab { padding: 10px 20px; font-size: 13px; font-weight: 500; color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.2s; }
			.agr-ft-tab:hover { color: var(--text-color); }
			.agr-ft-tab.active { color: var(--primary); border-bottom-color: var(--primary); }
			.agr-ft-tab-content { display: none; }
			.agr-ft-tab-content.active { display: block; }
			.agr-ft-summary { display: flex; gap: 20px; margin-bottom: 16px; flex-wrap: wrap; }
			.agr-ft-summary-card { background: var(--fg-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px 16px; min-width: 100px; }
			.agr-ft-summary-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 4px; }
			.agr-ft-summary-value { font-size: 18px; font-weight: 600; color: var(--text-color); }
			.agr-ft-summary-count { font-size: 11px; color: var(--text-muted); }
			.agr-ft-table { font-size: 12px; }
			.agr-ft-table th { font-weight: 600; background: var(--bg-color); }
			.agr-ft-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; }
			.agr-ft-badge.salik { background: #dbeafe; color: #1d4ed8; }
			.agr-ft-badge.darb { background: #fef3c7; color: #b45309; }
			.agr-ft-badge.fine { background: #fee2e2; color: #b91c1c; }
			.agr-ft-badge.paid { background: #dcfce7; color: #166534; }
			.agr-ft-badge.unpaid { background: #fef9c3; color: #854d0e; }
			.agr-ft-badge.charged { background: #e9d5ff; color: #7c3aed; }
		</style>`).appendTo('head');
	}

	const htmlContent = `
		<div class="agr-ft-container">
			<div class="agr-ft-tabs">
				<div class="agr-ft-tab active" data-tab="all">All</div>
				<div class="agr-ft-tab" data-tab="salik">Salik</div>
				<div class="agr-ft-tab" data-tab="darb">Darb</div>
				<div class="agr-ft-tab" data-tab="fines">Traffic Fines</div>
			</div>
			<div>
				<div class="agr-ft-tab-content active" id="agr-ft-tab-all"><div class="text-muted">Loading...</div></div>
				<div class="agr-ft-tab-content" id="agr-ft-tab-salik"></div>
				<div class="agr-ft-tab-content" id="agr-ft-tab-darb"></div>
				<div class="agr-ft-tab-content" id="agr-ft-tab-fines"></div>
			</div>
		</div>
	`;

	frm.set_df_property('fines_tolls_html', 'options', htmlContent);
	frm.refresh_field('fines_tolls_html');

	setTimeout(() => {
		$('.agr-ft-tab').off('click').on('click', function() {
			const tab = $(this).data('tab');
			$('.agr-ft-tab').removeClass('active');
			$(this).addClass('active');
			$('.agr-ft-tab-content').removeClass('active');
			$(`#agr-ft-tab-${tab}`).addClass('active');
		});

		loadAgreementFinesTolls(frm, agreement_type);
	}, 100);
}

async function loadAgreementFinesTolls(frm, agreement_type) {
	const { message } = await frappe.call({
		method: 'right_hire.api.fines_tolls.get_agreement_fines_tolls',
		args: { agreement_type: agreement_type, agreement_no: frm.doc.name, page: 1, page_len: 100 },
		freeze: false
	});

	const items = message?.data || [];
	const summary = message?.summary || {};

	const salik = items.filter(i => i.type === 'Salik');
	const darb = items.filter(i => i.type === 'Darb');
	const fines = items.filter(i => i.type === 'Traffic Fine');

	const allHtml = `
		<div class="agr-ft-summary">
			<div class="agr-ft-summary-card">
				<div class="agr-ft-summary-label">Total</div>
				<div class="agr-ft-summary-value">AED ${formatCurrencySimple(summary.grand_total || 0)}</div>
				<div class="agr-ft-summary-count">${items.length} records</div>
			</div>
			<div class="agr-ft-summary-card">
				<div class="agr-ft-summary-label">Salik</div>
				<div class="agr-ft-summary-value">AED ${formatCurrencySimple(summary.salik_total || 0)}</div>
				<div class="agr-ft-summary-count">${summary.salik_count || 0} trips</div>
			</div>
			<div class="agr-ft-summary-card">
				<div class="agr-ft-summary-label">Darb</div>
				<div class="agr-ft-summary-value">AED ${formatCurrencySimple(summary.darb_total || 0)}</div>
				<div class="agr-ft-summary-count">${summary.darb_count || 0} trips</div>
			</div>
			<div class="agr-ft-summary-card">
				<div class="agr-ft-summary-label">Traffic Fines</div>
				<div class="agr-ft-summary-value">AED ${formatCurrencySimple(summary.fines_total || 0)}</div>
				<div class="agr-ft-summary-count">${summary.fines_count || 0} fines</div>
			</div>
		</div>
		${renderAgrFinesTollsTable(items)}
	`;
	$('#agr-ft-tab-all').html(allHtml);
	$('#agr-ft-tab-salik').html(renderAgrFinesTollsTable(salik, 'Salik'));
	$('#agr-ft-tab-darb').html(renderAgrFinesTollsTable(darb, 'Darb'));
	$('#agr-ft-tab-fines').html(renderAgrFinesTollsTable(fines, 'Traffic Fine'));
}

function renderAgrFinesTollsTable(items, type = null) {
	if (!items.length) {
		return `<div class="text-muted text-center py-4">No ${type || 'fines or tolls'} found</div>`;
	}

	return `
		<div class="table-responsive">
			<table class="table table-bordered table-sm table-hover agr-ft-table">
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
							${!type ? `<td><span class="agr-ft-badge ${item.type.toLowerCase().replace(' ', '')}">${item.type}</span></td>` : ''}
							<td><a href="/app/vehicle/${item.vehicle}">${item.vehicle || '-'}</a></td>
							<td>${frappe.utils.escape_html(item.location || item.details || '-')}</td>
							<td style="text-align:right; font-weight:500;">AED ${formatCurrencySimple(item.amount || 0)}</td>
							<td><span class="agr-ft-badge ${item.status === 'Paid' ? 'paid' : 'unpaid'}">${item.status || 'Unpaid'}</span></td>
							<td>${item.charged_to_customer ? '<span class="agr-ft-badge charged">Charged</span>' : '-'}</td>
							<td><a href="/app/${item.doctype.toLowerCase().replace(/ /g, '-')}/${item.name}" class="btn btn-xs btn-default">View</a></td>
						</tr>
					`}).join('')}
				</tbody>
			</table>
		</div>
	`;
}

function formatCurrencySimple(value) {
	return (value || 0).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}
