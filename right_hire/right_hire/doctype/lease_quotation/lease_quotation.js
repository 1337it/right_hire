frappe.ui.form.on('Lease Quotation', {
    refresh: function(frm) {
        if (!frm.is_new() && !frm.doc.lease_contract) {
            // Generate Lease Contract button
            if (frm.doc.quotation_status === 'Sent' || frm.doc.quotation_status === 'Draft') {
                frm.add_custom_button(__('Generate Lease Contract'), function() {
                    frappe.confirm(
                        __('Are you sure you want to generate a Lease Contract from this quotation?'),
                        function() {
                            frappe.call({
                                method: 'generate_lease_contract',
                                doc: frm.doc,
                                callback: function(r) {
                                    if (r.message && r.message.success) {
                                        frappe.msgprint(__('Lease Contract {0} created successfully', [r.message.contract]));
                                        frm.reload_doc();
                                        frappe.set_route('Form', 'Lease Contract', r.message.contract);
                                    }
                                }
                            });
                        }
                    );
                }).addClass('btn-primary');
            }
        }

        // View linked Lease Contract
        if (frm.doc.lease_contract) {
            frm.add_custom_button(__('View Lease Contract'), function() {
                frappe.set_route('Form', 'Lease Contract', frm.doc.lease_contract);
            });
        }
    },

    rate_plan: function(frm) {
        if (frm.doc.rate_plan) {
            frappe.db.get_doc('Rate Plan', frm.doc.rate_plan).then(rate_plan => {
                frm.set_value('monthly_rate', rate_plan.base_rate);
                frm.set_value('deposit_amount', rate_plan.deposit);
                calculate_amounts(frm);
            });
        }
    },

    start_date: function(frm) {
        calculate_end_date(frm);
    },

    lease_duration_months: function(frm) {
        calculate_end_date(frm);
        calculate_amounts(frm);
    },

    monthly_rate: function(frm) {
        calculate_amounts(frm);
    }
});

function calculate_end_date(frm) {
    if (frm.doc.start_date && frm.doc.lease_duration_months) {
        let start = frappe.datetime.str_to_obj(frm.doc.start_date);
        start.setMonth(start.getMonth() + parseInt(frm.doc.lease_duration_months));
        frm.set_value('end_date', frappe.datetime.obj_to_str(start));
    }
}

function calculate_amounts(frm) {
    if (frm.doc.monthly_rate && frm.doc.lease_duration_months) {
        frm.set_value('total_amount', flt(frm.doc.monthly_rate) * flt(frm.doc.lease_duration_months));
    }
}
