frappe.ui.form.on('Lease Quotation', {
    refresh: function(frm) {
        if (!frm.doc.__islocal && frm.doc.quotation_status !== 'Accepted') {
            frm.add_custom_button(__('Generate Lease Contract'), function() {
                // Call the server method to get quotation items
                frappe.call({
                    method: 'generate_lease_contract',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message && r.message.items && r.message.items.length > 0) {
                            // Show dialog to select vehicle/plan
                            show_item_selection_dialog(frm, r.message.items);
                        }
                    }
                });
            });
        }
    },

    quotation_date: function(frm) {
        if (frm.doc.quotation_date && !frm.doc.valid_until) {
            // Auto-set valid_until to 7 days from quotation_date
            let valid_until = frappe.datetime.add_days(frm.doc.quotation_date, 7);
            frm.set_value('valid_until', valid_until);
        }
    }
});

function show_item_selection_dialog(frm, items) {
    let fields = [];

    // Create radio buttons for each item
    items.forEach((item, idx) => {
        let mileage_text = item.annual_mileage ? `${item.annual_mileage.toLocaleString()} kms/year` : '';
        fields.push({
            fieldtype: 'HTML',
            fieldname: 'item_' + idx,
            options: `
                <div style="padding: 10px; margin: 5px 0; border: 1px solid #d1d8dd; border-radius: 4px; cursor: pointer;"
                     class="item-option" data-idx="${idx}">
                    <div style="font-weight: 600; font-size: 14px;">${item.vehicle}</div>
                    <div style="color: #6c757d; font-size: 12px; margin-top: 5px;">${mileage_text}</div>
                    <div style="color: #27AE60; font-weight: 600; font-size: 16px; margin-top: 5px;">
                        ${format_currency(item.price_per_month, frm.doc.currency || 'AED')} / month
                    </div>
                </div>
            `
        });
    });

    let d = new frappe.ui.Dialog({
        title: __('Select Vehicle & Plan'),
        fields: fields,
        primary_action_label: __('Create Contract'),
        primary_action: function() {
            let selected_idx = d.$wrapper.find('.item-option.selected').data('idx');
            if (selected_idx === undefined) {
                frappe.msgprint(__('Please select a vehicle option'));
                return;
            }

            // Call create_contract_from_item
            frappe.call({
                method: 'create_contract_from_item',
                doc: frm.doc,
                args: {
                    item_idx: selected_idx
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        d.hide();
                        frm.reload_doc();
                        frappe.set_route('Form', 'Lease Contract', r.message.contract);
                    }
                }
            });
        }
    });

    // Add click handlers for selection
    d.$wrapper.on('click', '.item-option', function() {
        d.$wrapper.find('.item-option').removeClass('selected');
        d.$wrapper.find('.item-option').css('background-color', '');
        $(this).addClass('selected');
        $(this).css('background-color', '#e8f5e9');
    });

    d.show();
}
