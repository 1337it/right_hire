frappe.ui.form.on('Rental Quotation', {
    refresh: function(frm) {
        if (!frm.is_new() && !frm.doc.rental_agreement) {
            // Generate Rental Agreement button
            if (frm.doc.quotation_status === 'Sent' || frm.doc.quotation_status === 'Draft') {
                frm.add_custom_button(__('Generate Rental Agreement'), function() {
                    frappe.confirm(
                        __('Are you sure you want to generate a Rental Agreement from this quotation?'),
                        function() {
                            frappe.call({
                                method: 'generate_rental_agreement',
                                doc: frm.doc,
                                callback: function(r) {
                                    if (r.message && r.message.success) {
                                        frappe.msgprint(__('Rental Agreement {0} created successfully', [r.message.agreement]));
                                        frm.reload_doc();
                                        frappe.set_route('Form', 'Rental Agreement', r.message.agreement);
                                    }
                                }
                            });
                        }
                    );
                }).addClass('btn-primary');
            }
        }

        // View linked Rental Agreement
        if (frm.doc.rental_agreement) {
            frm.add_custom_button(__('View Rental Agreement'), function() {
                frappe.set_route('Form', 'Rental Agreement', frm.doc.rental_agreement);
            });
        }
    },

    rate_plan: function(frm) {
        if (frm.doc.rate_plan) {
            frappe.db.get_doc('Rate Plan', frm.doc.rate_plan).then(rate_plan => {
                frm.set_value('base_rate', rate_plan.base_rate);
                frm.set_value('deposit_amount', rate_plan.deposit);
                calculate_amounts(frm);
            });
        }
    },

    start_datetime: function(frm) {
        calculate_days(frm);
    },

    end_datetime: function(frm) {
        calculate_days(frm);
    }
});

frappe.ui.form.on('Quotation Extra', {
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

function calculate_days(frm) {
    if (frm.doc.start_datetime && frm.doc.end_datetime) {
        let start = moment(frm.doc.start_datetime);
        let end = moment(frm.doc.end_datetime);
        let hours = end.diff(start, 'hours', true);
        frm.set_value('planned_days', hours / 24);
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
    if (frm.doc.base_rate && frm.doc.planned_days) {
        frm.set_value('rental_amount', flt(frm.doc.base_rate) * flt(frm.doc.planned_days));
    }

    let extras_total = 0;
    (frm.doc.extras || []).forEach(function(extra) {
        extras_total += flt(extra.amount);
    });
    frm.set_value('extras_total', extras_total);

    frm.set_value('grand_total', flt(frm.doc.rental_amount) + extras_total);
}
