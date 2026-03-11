// Copyright (c) 2025, Right Hire and contributors
// For license information, please see license.txt

// Vehicle doctype client script
frappe.ui.form.on('Vehicle', {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      // Load panels directly on refresh
      setTimeout(() => {
        render_panel(frm);
        render_fines_tolls_panel(frm);
      }, 300);
    } else {
      frm.set_df_property('movement_logs_html', 'options',
        `<div class="text-muted">Save the vehicle first to view movement logs.</div>`);
      frm.set_df_property('fines_tolls_html', 'options',
        `<div class="text-muted">Save the vehicle first to view fines and tolls.</div>`);
    }

    // Add a shortcut to create a Movement prefilled with this vehicle
    if (!frm.is_new()) {
      frm.add_custom_button('New Vehicle Movement', () => {
        frappe.new_doc('Movement', {
          vehicle: frm.doc.name
        });
      }, __('Actions'));
    }

    // Add scan insurance button if document is uploaded
    if (frm.doc.insurance_document && !frm.is_new()) {
      add_scan_insurance_button(frm);
    }

    // Reset the insurance scan flag on refresh
    frm._insurance_scan_asked = false;
  },

  after_save(frm) {
    setTimeout(() => {
      render_panel(frm);
      render_fines_tolls_panel(frm);
    }, 300);
    // Reset flag after save so it can be asked again if document changes
    frm._insurance_scan_asked = false;
  },

  update_odometer: function(frm, cdt, cdn) {
    frappe.call({
      method: "right_hire.right_hire.doctype.Vehicle.Vehicle.update_odometer",
      args: {
        docname: frm.doc.name
      },
      callback: function(r) {
        frappe.model.set_value(cdt, cdn, 'last_odometer_value', r.message);
      }
    });
  },

  // Live update custom_plate_art when custom_plate_code changes
  custom_plate_code: function(frm) {
    update_plate_art_live(frm);
  },

  // Live update custom_plate_art when plate_no changes
  plate_no: function(frm) {
    update_plate_art_live(frm);
  },

  // Handle insurance document upload - ask if user wants to scan
  insurance_document: function(frm) {
    if (frm.doc.insurance_document && !frm._insurance_scan_asked) {
      // Set flag to prevent repeated prompts
      frm._insurance_scan_asked = true;

      // Wait a bit for the file to be fully uploaded
      setTimeout(function() {
        frappe.confirm(
          __('Do you want to scan this insurance policy document and automatically extract policy details?'),
          function() {
            // Yes - scan the document
            scan_insurance_document_and_save(frm);
          },
          function() {
            // No - just continue
            frappe.show_alert({
              message: __('You can scan the document later using Actions > Scan Insurance Policy'),
              indicator: 'blue'
            }, 5);
          }
        );
      }, 500);
    }
  }
});

// Function to update plate art in real-time
function update_plate_art_live(frm) {
  const plate_code = frm.doc.custom_plate_code || '';
  const plate_no = frm.doc.plate_no || '';

  let plate_art = '';

  if (plate_code && plate_no) {
    plate_art = `${plate_code} ${plate_no}`;
  } else if (plate_no) {
    plate_art = plate_no;
  } else if (plate_code) {
    plate_art = plate_code;
  }

  frm.set_value('custom_plate_art', plate_art);
}

function render_panel(frm) {
  // Add CSS for split layout and Apple-like timeline
  if (!document.getElementById('movement-logs-styles')) {
    $(`<style id="movement-logs-styles">
      .movement-logs-container { display: flex; gap: 24px; min-height: 400px; }
      .movements-list-panel { flex: 1; min-width: 0; }
      .timeline-panel { width: 280px; flex-shrink: 0; max-height: 500px; overflow-y: auto; padding-left: 24px; border-left: 1px solid rgba(0,0,0,0.06); }
      .timeline-panel::-webkit-scrollbar { width: 4px; }
      .timeline-panel::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 2px; }
      .timeline-header { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 16px; }
      .tl-item { position: relative; padding-left: 20px; padding-bottom: 20px; }
      .tl-item:last-child { padding-bottom: 0; }
      .tl-item::before { content: ''; position: absolute; left: 0; top: 6px; width: 8px; height: 8px; border-radius: 50%; background: #d1d5db; }
      .tl-item::after { content: ''; position: absolute; left: 3.5px; top: 18px; width: 1px; height: calc(100% - 12px); background: #e5e7eb; }
      .tl-item:last-child::after { display: none; }
      .tl-item.color-green::before { background: #22c55e; }
      .tl-item.color-blue::before { background: #3b82f6; }
      .tl-item.color-orange::before { background: #f97316; }
      .tl-item.color-red::before { background: #ef4444; }
      .tl-item.color-purple::before { background: #a855f7; }
      .tl-item.color-yellow::before { background: #eab308; }
      .tl-item.color-gray::before { background: #9ca3af; }
      .tl-title { font-size: 13px; font-weight: 500; color: var(--text-color); line-height: 1.3; }
      .tl-title a { color: inherit; text-decoration: none; }
      .tl-title a:hover { color: var(--primary); }
      .tl-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
      .tl-date { font-size: 11px; color: var(--text-light); margin-top: 4px; }
      @media (max-width: 768px) {
        .movement-logs-container { flex-direction: column; }
        .timeline-panel { width: 100%; max-height: 300px; border-left: none; border-top: 1px solid rgba(0,0,0,0.06); padding-left: 0; padding-top: 16px; }
      }
    </style>`).appendTo('head');
  }

  // Build HTML content
  const htmlContent = `
    <div class="movement-logs-container">
      <div class="movements-list-panel">
        <div class="flex items-center gap-2" style="margin-bottom:8px; flex-wrap: wrap;">
          <input type="date" class="form-control" id="vm_from" placeholder="From" style="max-width: 140px;">
          <input type="date" class="form-control" id="vm_to" placeholder="To" style="max-width: 140px;">
          <select class="form-control" id="vm_type" style="max-width: 180px;">
            <option value="">All Types</option>
            <option value="NRM - Customer">Customer Movement</option>
            <option value="NRM - Staff">Staff Movement</option>
            <option value="Workshop">Workshop</option>
            <option value="Custody">Custody</option>
            <option value="Delivery">Delivery</option>
            <option value="Recovery">Recovery</option>
          </select>
          <button class="btn btn-sm btn-primary" id="vm_refresh">Filter</button>
        </div>
        <div id="vm_table"><div class="text-muted">Loading...</div></div>
        <div class="flex items-center justify-between" style="margin-top:8px;">
          <div class="text-muted small" id="vm_count"></div>
          <div class="btn-group">
            <button class="btn btn-xs btn-default" id="vm_prev">Prev</button>
            <button class="btn btn-xs btn-default" id="vm_next">Next</button>
          </div>
        </div>
      </div>
      <div class="timeline-panel">
        <div class="timeline-header">Timeline</div>
        <div id="vm_timeline"><div class="text-muted small">Loading...</div></div>
      </div>
    </div>
  `;

  frm.set_df_property('movement_logs_html', 'options', htmlContent);
  frm.refresh_field('movement_logs_html');

  // Wait for DOM to update then attach event handlers and load data
  setTimeout(() => {
    let page = 1;
    const page_len = 10;

    async function loadMovements() {
      const from = $('#vm_from').val() || null;
      const to = $('#vm_to').val() || null;
      const mtype = $('#vm_type').val() || null;

      const { message } = await frappe.call({
        method: 'right_hire.api.movements.get_vehicle_movements',
        args: { vehicle: frm.doc.name, from_date: from, to_date: to, movement_type: mtype, page, page_len },
        freeze: false
      });

      const rows = message?.data || [];
      const total = message?.total || 0;

      $('#vm_count').text(total ? `${total} record(s)` : 'No records');

      const html = rows.length ? `
        <div class="table-responsive">
          <table class="table table-bordered table-sm table-hover" style="font-size: 12px;">
            <thead><tr><th>Out Date/Time</th><th>In Date/Time</th><th>ID</th><th>Type</th><th>Status</th><th>Customer/Staff</th><th>Agreement</th></tr></thead>
            <tbody>
              ${rows.map(r => {
                const outDt = r.out_date_time ? frappe.datetime.str_to_user(r.out_date_time.substring(0, 16)) : '-';
                const inDt = r.in_date_time ? frappe.datetime.str_to_user(r.in_date_time.substring(0, 16)) : '-';
                return `
                <tr>
                  <td style="white-space:nowrap;">${outDt}</td>
                  <td style="white-space:nowrap;">${inDt}</td>
                  <td><a class="bold" href="/app/movements/${encodeURIComponent(r.name)}">${r.name}</a></td>
                  <td>${frappe.utils.escape_html(r.movement_type || '')}</td>
                  <td><span class="indicator-pill ${r.status === 'Returned' ? 'green' : r.status === 'Out Only' ? 'blue' : 'gray'}">${r.status || ''}</span></td>
                  <td>${frappe.utils.escape_html(r.out_customer || r.in_customer || r.out_staff || r.in_staff || '-')}</td>
                  <td>${r.agreement_no ? `<a href="/app/${(r.agreement_type || '').toLowerCase().replace(/ /g, '-')}/${r.agreement_no}">${r.agreement_no}</a>` : '-'}</td>
                </tr>
              `}).join('')}
            </tbody>
          </table>
        </div>
      ` : '<div class="text-muted text-center py-4">No movements found</div>';

      $('#vm_table').html(html);
      const max_page = Math.max(1, Math.ceil(total / page_len));
      $('#vm_prev').prop('disabled', page <= 1);
      $('#vm_next').prop('disabled', page >= max_page);
    }

    async function loadTimeline() {
      const { message } = await frappe.call({
        method: 'right_hire.api.movements.get_vehicle_timeline',
        args: { vehicle: frm.doc.name },
        freeze: false
      });

      const events = message || [];
      if (!events.length) {
        $('#vm_timeline').html('<div class="text-muted small">No events yet</div>');
        return;
      }

      const html = events.map(e => `
        <div class="tl-item color-${e.color || 'gray'}">
          <div class="tl-title">${e.link ? `<a href="${e.link}">${frappe.utils.escape_html(e.title)}</a>` : frappe.utils.escape_html(e.title)}</div>
          ${e.subtitle ? `<div class="tl-subtitle">${frappe.utils.escape_html(e.subtitle)}</div>` : ''}
          <div class="tl-date">${frappe.datetime.str_to_user(e.date) || e.date}</div>
        </div>
      `).join('');

      $('#vm_timeline').html(html);
    }

    // Event handlers
    $('#vm_refresh').off('click').on('click', () => { page = 1; loadMovements(); });
    $('#vm_prev').off('click').on('click', () => { if (page > 1) { page--; loadMovements(); } });
    $('#vm_next').off('click').on('click', () => { page++; loadMovements(); });

    // Initial load
    loadMovements();
    loadTimeline();
  }, 100);
}

// ==================== INSURANCE POLICY SCANNING ====================

function add_scan_insurance_button(frm) {
  // Remove existing button first to avoid duplicates (safely)
  try {
    frm.remove_custom_button(__('Scan Insurance Policy'), __('Actions'));
  } catch(e) { /* button may not exist */ }

  // Add the scan button
  frm.add_custom_button(__('Scan Insurance Policy'), function() {
    scan_insurance_document(frm);
  }, __('Actions'));
}

function scan_insurance_document(frm) {
  if (!frm.doc.insurance_document) {
    frappe.msgprint({
      title: __('No Document'),
      message: __('Please upload an insurance policy document first.'),
      indicator: 'red'
    });
    return;
  }

  // Show loading indicator
  frappe.dom.freeze(__('Scanning insurance policy document...<br><small>Extracting policy details using Azure Document Intelligence</small>'));

  // Call the Azure DI scan function
  frappe.call({
    method: 'right_hire.right_hire.azure_di.scan_insurance_policy',
    args: {
      file_url: frm.doc.insurance_document,
      use_urlsource: 0,
      debug: 1
    },
    callback: function(r) {
      frappe.dom.unfreeze();

      if (r.message && r.message.fields) {
        const fields = r.message.fields;

        // Show confirmation dialog before populating
        frappe.confirm(
          __('Insurance policy scanned successfully! Found: {0}<br><br>Do you want to populate the fields with extracted data?',
            [build_scan_summary(fields)]),
          function() {
            populate_insurance_fields(frm, fields);
          }
        );
      } else {
        frappe.msgprint({
          title: __('Scan Failed'),
          message: __('Unable to extract data from the insurance policy document. Please check the document quality and try again.'),
          indicator: 'red'
        });
      }
    },
    error: function(err) {
      frappe.dom.unfreeze();
      frappe.msgprint({
        title: __('Error'),
        message: __('Failed to scan insurance policy. Please try again.'),
        indicator: 'red'
      });
      console.error('Insurance Policy Scan Error:', err);
    }
  });
}

function scan_insurance_document_and_save(frm) {
  if (!frm.doc.insurance_document) {
    frappe.msgprint({
      title: __('No Document'),
      message: __('Please upload an insurance policy document first.'),
      indicator: 'red'
    });
    return;
  }

  frappe.dom.freeze(__('Scanning insurance policy document...<br><small>Extracting policy details using Azure Document Intelligence</small>'));

  frappe.call({
    method: 'right_hire.right_hire.azure_di.scan_insurance_policy',
    args: {
      file_url: frm.doc.insurance_document,
      use_urlsource: 0,
      debug: 1
    },
    callback: function(r) {
      frappe.dom.unfreeze();

      if (r.message && r.message.fields) {
        const fields = r.message.fields;

        frappe.show_alert({
          message: __('Scanning complete! Found {0} details. Populating fields...',
            [count_extracted_fields(fields)]),
          indicator: 'green'
        }, 5);

        populate_insurance_fields_and_save(frm, fields);
      } else {
        frappe.msgprint({
          title: __('Scan Failed'),
          message: __('Unable to extract data from the insurance policy document. Please check the document quality and try again.'),
          indicator: 'orange'
        });
      }
    },
    error: function(err) {
      frappe.dom.unfreeze();
      frappe.msgprint({
        title: __('Error'),
        message: __('Failed to scan insurance policy. Please try again.'),
        indicator: 'red'
      });
      console.error('Insurance Policy Scan Error:', err);
    }
  });
}

function build_scan_summary(fields) {
  let summary = '<ul style="text-align: left; margin: 10px 0;">';

  if (fields.policy_number) {
    summary += `<li><strong>Policy Number:</strong> ${fields.policy_number}</li>`;
  }
  if (fields.insurance_provider) {
    summary += `<li><strong>Insurance Provider:</strong> ${fields.insurance_provider}</li>`;
  }
  if (fields.insured_name) {
    summary += `<li><strong>Insured Name:</strong> ${fields.insured_name}</li>`;
  }
  if (fields.coverage_type) {
    summary += `<li><strong>Coverage Type:</strong> ${fields.coverage_type}</li>`;
  }
  if (fields.premium_amount) {
    summary += `<li><strong>Premium Amount:</strong> ${format_currency(fields.premium_amount)}</li>`;
  }
  if (fields.policy_start_date && fields.insurance_expiry) {
    summary += `<li><strong>Policy Period:</strong> ${fields.policy_start_date} to ${fields.insurance_expiry}</li>`;
  }
  if (fields.policy_conditions && fields.policy_conditions.length > 0) {
    summary += `<li><strong>Coverage Items:</strong> ${fields.policy_conditions.length} items found</li>`;
  }

  summary += '</ul>';
  return summary;
}

function populate_insurance_fields(frm, fields) {
  const field_mapping = {
    'policy_number': 'policy_number',
    'insurance_provider': 'insurance_provider',
    'insured_name': 'insured_name',
    'policy_start_date': 'policy_start_date',
    'insurance_expiry': 'insurance_expiry',
    'premium_amount': 'premium_amount',
    'coverage_type': 'coverage_type',
    'sum_insured': 'sum_insured'
  };

  let updated_count = 0;

  for (let source_field in field_mapping) {
    let target_field = field_mapping[source_field];
    if (fields[source_field] && fields[source_field] !== null) {
      frm.set_value(target_field, fields[source_field]);
      updated_count++;
    }
  }

  // Populate policy conditions table
  if (fields.policy_conditions && fields.policy_conditions.length > 0) {
    frappe.confirm(
      __('Do you want to replace existing policy conditions ({0} items) with {1} newly extracted items?',
        [frm.doc.insurance_policy_conditions ? frm.doc.insurance_policy_conditions.length : 0,
         fields.policy_conditions.length]),
      function() {
        frm.clear_table('insurance_policy_conditions');

        fields.policy_conditions.forEach(function(condition) {
          let row = frm.add_child('insurance_policy_conditions');
          row.coverage_item = condition.coverage_item || 'Other';
          row.description = condition.description || '';
          row.coverage_amount = condition.coverage_amount || 0;
          row.deductible = condition.deductible || 0;
        });

        frm.refresh_field('insurance_policy_conditions');

        frappe.show_alert({
          message: __('Added {0} policy conditions', [fields.policy_conditions.length]),
          indicator: 'green'
        }, 5);
      },
      function() {
        fields.policy_conditions.forEach(function(condition) {
          let row = frm.add_child('insurance_policy_conditions');
          row.coverage_item = condition.coverage_item || 'Other';
          row.description = condition.description || '';
          row.coverage_amount = condition.coverage_amount || 0;
          row.deductible = condition.deductible || 0;
        });

        frm.refresh_field('insurance_policy_conditions');

        frappe.show_alert({
          message: __('Appended {0} policy conditions', [fields.policy_conditions.length]),
          indicator: 'green'
        }, 5);
      }
    );
  }

  frm.dirty();

  frappe.show_alert({
    message: __('Insurance policy data extracted successfully! Updated {0} fields.', [updated_count]),
    indicator: 'green'
  }, 10);

  if (fields.policy_conditions && fields.policy_conditions.length > 0) {
    show_extracted_conditions_dialog(fields.policy_conditions);
  }
}

function show_extracted_conditions_dialog(conditions) {
  let html = '<div class="insurance-conditions">';
  html += '<h4>Extracted Policy Coverage Items</h4>';
  html += '<table class="table table-bordered table-sm">';
  html += '<thead><tr><th>Coverage Item</th><th>Description</th><th>Amount</th><th>Deductible</th></tr></thead>';
  html += '<tbody>';

  conditions.forEach(function(condition) {
    html += '<tr>';
    html += `<td><strong>${frappe.utils.escape_html(condition.coverage_item || '')}</strong></td>`;
    html += `<td>${frappe.utils.escape_html(condition.description || '-')}</td>`;
    html += `<td>${condition.coverage_amount ? format_currency(condition.coverage_amount) : '-'}</td>`;
    html += `<td>${condition.deductible ? format_currency(condition.deductible) : '-'}</td>`;
    html += '</tr>';
  });

  html += '</tbody></table></div>';

  frappe.msgprint({
    title: __('Extracted Coverage Details'),
    message: html,
    indicator: 'blue',
    wide: true
  });
}

function count_extracted_fields(fields) {
  let count = 0;
  const checkFields = [
    'policy_number', 'insurance_provider', 'insured_name',
    'policy_start_date', 'insurance_expiry', 'premium_amount',
    'coverage_type', 'sum_insured'
  ];

  checkFields.forEach(function(field) {
    if (fields[field] && fields[field] !== null) {
      count++;
    }
  });

  if (fields.policy_conditions && fields.policy_conditions.length > 0) {
    count += fields.policy_conditions.length;
  }

  return count;
}

function populate_insurance_fields_and_save(frm, fields) {
  const field_mapping = {
    'policy_number': 'policy_number',
    'insurance_provider': 'insurance_provider',
    'insured_name': 'insured_name',
    'policy_start_date': 'policy_start_date',
    'insurance_expiry': 'insurance_expiry',
    'premium_amount': 'premium_amount',
    'coverage_type': 'coverage_type',
    'sum_insured': 'sum_insured'
  };

  let updated_count = 0;

  for (let source_field in field_mapping) {
    let target_field = field_mapping[source_field];
    if (fields[source_field] && fields[source_field] !== null) {
      frm.set_value(target_field, fields[source_field]);
      updated_count++;
    }
  }

  if (fields.policy_conditions && fields.policy_conditions.length > 0) {
    frm.clear_table('insurance_policy_conditions');

    fields.policy_conditions.forEach(function(condition) {
      let row = frm.add_child('insurance_policy_conditions');
      row.coverage_item = condition.coverage_item || 'Other';
      row.description = condition.description || '';
      row.coverage_amount = condition.coverage_amount || 0;
      row.deductible = condition.deductible || 0;
    });

    frm.refresh_field('insurance_policy_conditions');
    updated_count += fields.policy_conditions.length;
  }

  frm.dirty();

  frappe.show_alert({
    message: __('Extracted {0} items. Saving...', [updated_count]),
    indicator: 'blue'
  }, 3);

  frm.save().then(function() {
    frappe.show_alert({
      message: __('Insurance policy data saved successfully!'),
      indicator: 'green'
    }, 5);

    if (fields.policy_conditions && fields.policy_conditions.length > 0) {
      setTimeout(function() {
        show_extracted_conditions_dialog(fields.policy_conditions);
      }, 1000);
    }
  }).catch(function(err) {
    frappe.msgprint({
      title: __('Save Failed'),
      message: __('Failed to save the extracted data. Please save manually.'),
      indicator: 'red'
    });
    console.error('Save error:', err);
  });
}

// ==================== FINES & TOLLS PANEL ====================

function render_fines_tolls_panel(frm) {
  // Add CSS for fines/tolls panel
  if (!document.getElementById('fines-tolls-styles')) {
    $(`<style id="fines-tolls-styles">
      .fines-tolls-container { min-height: 300px; }
      .ft-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-color); margin-bottom: 16px; }
      .ft-tab { padding: 10px 20px; font-size: 13px; font-weight: 500; color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.2s; }
      .ft-tab:hover { color: var(--text-color); }
      .ft-tab.active { color: var(--primary); border-bottom-color: var(--primary); }
      .ft-tab-content { display: none; }
      .ft-tab-content.active { display: block; }
      .ft-summary { display: flex; gap: 24px; margin-bottom: 16px; flex-wrap: wrap; }
      .ft-summary-card { background: var(--fg-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px 16px; min-width: 120px; }
      .ft-summary-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 4px; }
      .ft-summary-value { font-size: 20px; font-weight: 600; color: var(--text-color); }
      .ft-summary-count { font-size: 12px; color: var(--text-muted); }
      .ft-table { font-size: 12px; }
      .ft-table th { font-weight: 600; background: var(--bg-color); }
      .ft-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; }
      .ft-badge.salik { background: #dbeafe; color: #1d4ed8; }
      .ft-badge.darb { background: #fef3c7; color: #b45309; }
      .ft-badge.trafficfine { background: #fee2e2; color: #b91c1c; }
      .ft-badge.paid { background: #dcfce7; color: #166534; }
      .ft-badge.unpaid { background: #fef9c3; color: #854d0e; }
      .ft-badge.charged { background: #e9d5ff; color: #7c3aed; }
    </style>`).appendTo('head');
  }

  const htmlContent = `
    <div class="fines-tolls-container">
      <div class="ft-tabs">
        <div class="ft-tab active" data-tab="all">All</div>
        <div class="ft-tab" data-tab="salik">Salik</div>
        <div class="ft-tab" data-tab="darb">Darb</div>
        <div class="ft-tab" data-tab="fines">Traffic Fines</div>
      </div>
      <div>
        <div class="ft-tab-content active" id="ft-tab-all"><div class="text-muted">Loading...</div></div>
        <div class="ft-tab-content" id="ft-tab-salik"></div>
        <div class="ft-tab-content" id="ft-tab-darb"></div>
        <div class="ft-tab-content" id="ft-tab-fines"></div>
      </div>
    </div>
  `;

  frm.set_df_property('fines_tolls_html', 'options', htmlContent);
  frm.refresh_field('fines_tolls_html');

  setTimeout(() => {
    // Tab switching
    $('.ft-tab').off('click').on('click', function() {
      const tab = $(this).data('tab');
      $('.ft-tab').removeClass('active');
      $(this).addClass('active');
      $('.ft-tab-content').removeClass('active');
      $(`#ft-tab-${tab}`).addClass('active');
    });

    // Load data
    loadFinesTolls(frm);
  }, 100);
}

async function loadFinesTolls(frm) {
  const { message } = await frappe.call({
    method: 'right_hire.api.fines_tolls.get_vehicle_fines_tolls',
    args: { vehicle: frm.doc.name, page: 1, page_len: 100 },
    freeze: false
  });

  const items = message?.data || [];

  // Separate by type
  const salik = items.filter(i => i.type === 'Salik');
  const darb = items.filter(i => i.type === 'Darb');
  const fines = items.filter(i => i.type === 'Traffic Fine');

  // Calculate totals
  const salikTotal = salik.reduce((sum, i) => sum + (i.amount || 0), 0);
  const darbTotal = darb.reduce((sum, i) => sum + (i.amount || 0), 0);
  const finesTotal = fines.reduce((sum, i) => sum + (i.amount || 0), 0);
  const grandTotal = salikTotal + darbTotal + finesTotal;

  // Render All tab
  const allHtml = `
    <div class="ft-summary">
      <div class="ft-summary-card">
        <div class="ft-summary-label">Total</div>
        <div class="ft-summary-value">AED ${format_currency_simple(grandTotal)}</div>
        <div class="ft-summary-count">${items.length} records</div>
      </div>
      <div class="ft-summary-card">
        <div class="ft-summary-label">Salik</div>
        <div class="ft-summary-value">AED ${format_currency_simple(salikTotal)}</div>
        <div class="ft-summary-count">${salik.length} trips</div>
      </div>
      <div class="ft-summary-card">
        <div class="ft-summary-label">Darb</div>
        <div class="ft-summary-value">AED ${format_currency_simple(darbTotal)}</div>
        <div class="ft-summary-count">${darb.length} trips</div>
      </div>
      <div class="ft-summary-card">
        <div class="ft-summary-label">Traffic Fines</div>
        <div class="ft-summary-value">AED ${format_currency_simple(finesTotal)}</div>
        <div class="ft-summary-count">${fines.length} fines</div>
      </div>
    </div>
    ${renderFinesTollsTable(items)}
  `;
  $('#ft-tab-all').html(allHtml);

  // Render Salik tab
  $('#ft-tab-salik').html(renderFinesTollsTable(salik, 'Salik'));

  // Render Darb tab
  $('#ft-tab-darb').html(renderFinesTollsTable(darb, 'Darb'));

  // Render Fines tab
  $('#ft-tab-fines').html(renderFinesTollsTable(fines, 'Traffic Fine'));
}

function renderFinesTollsTable(items, type = null) {
  if (!items.length) {
    return `<div class="text-muted text-center py-4">No ${type || 'fines or tolls'} found</div>`;
  }

  return `
    <div class="table-responsive">
      <table class="table table-bordered table-sm table-hover ft-table">
        <thead>
          <tr>
            <th>Date/Time</th>
            ${!type ? '<th>Type</th>' : ''}
            <th>Location</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Agreement</th>
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
              ${!type ? `<td><span class="ft-badge ${item.type.toLowerCase().replace(' ', '')}">${item.type}</span></td>` : ''}
              <td>${frappe.utils.escape_html(item.location || item.details || '-')}</td>
              <td style="text-align:right; font-weight:500;">AED ${format_currency_simple(item.amount || 0)}</td>
              <td><span class="ft-badge ${item.status === 'Paid' ? 'paid' : 'unpaid'}">${item.status || 'Unpaid'}</span></td>
              <td>${item.linked_contract ? `<a href="/app/lease-agreement/${item.linked_contract}">${item.linked_contract}</a>` :
                    item.linked_agreement ? `<a href="/app/rental-agreement/${item.linked_agreement}">${item.linked_agreement}</a>` : '-'}</td>
              <td>${item.charged_to_customer ? '<span class="ft-badge charged">Charged</span>' : '-'}</td>
              <td><a href="/app/${item.doctype.toLowerCase().replace(/ /g, '-')}/${item.name}" class="btn btn-xs btn-default">View</a></td>
            </tr>
          `}).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function format_currency_simple(value) {
  return (value || 0).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}
