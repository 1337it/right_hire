frappe.ui.form.on('Lease to Own Quotation', {
    refresh: function(frm) {
        if (!frm.is_new() && !frm.doc.lease_to_own) {
            // Generate Lease to Own Contract button
            if (frm.doc.quotation_status === 'Sent' || frm.doc.quotation_status === 'Draft') {
                frm.add_custom_button(__('Generate Lease to Own Contract'), function() {
                    frappe.confirm(
                        __('Are you sure you want to generate a Lease to Own Contract from this quotation?'),
                        function() {
                            frappe.call({
                                method: 'generate_lease_to_own',
                                doc: frm.doc,
                                callback: function(r) {
                                    if (r.message && r.message.success) {
                                        frappe.msgprint(__('Lease to Own Contract {0} created successfully', [r.message.contract]));
                                        frm.reload_doc();
                                        frappe.set_route('Form', 'Lease to Own', r.message.contract);
                                    }
                                }
                            });
                        }
                    );
                }).addClass('btn-primary');
            }
        }

        // View linked Lease to Own Contract
        if (frm.doc.lease_to_own) {
            frm.add_custom_button(__('View Lease to Own Contract'), function() {
                frappe.set_route('Form', 'Lease to Own', frm.doc.lease_to_own);
            });
        }
    },

    start_date: function(frm) {
        calculate_end_date(frm);
    },

    contract_duration_months: function(frm) {
        calculate_end_date(frm);
        calculate_amounts(frm);
    },

    monthly_payment: function(frm) {
        calculate_amounts(frm);
    },

    down_payment: function(frm) {
        calculate_amounts(frm);
    },

    final_payment: function(frm) {
        calculate_amounts(frm);
    }
});

function calculate_end_date(frm) {
    if (frm.doc.start_date && frm.doc.contract_duration_months) {
        let start = frappe.datetime.str_to_obj(frm.doc.start_date);
        start.setMonth(start.getMonth() + parseInt(frm.doc.contract_duration_months));
        frm.set_value('end_date', frappe.datetime.obj_to_str(start));
    }
}

function calculate_amounts(frm) {
    if (frm.doc.monthly_payment && frm.doc.contract_duration_months) {
        frm.set_value('number_of_payments', parseInt(frm.doc.contract_duration_months));

        let total_monthly = flt(frm.doc.monthly_payment) * flt(frm.doc.contract_duration_months);
        let total = total_monthly + flt(frm.doc.down_payment) + flt(frm.doc.final_payment);
        frm.set_value('total_amount', total);
    }

    if (frm.doc.total_amount && frm.doc.down_payment) {
        frm.set_value('financed_amount', flt(frm.doc.total_amount) - flt(frm.doc.down_payment));
    }
}
