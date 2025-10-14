frappe.ui.form.on('Rental Agreement', {
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
            }
        }
    }
});
