frappe.ui.form.on('Customer', {
    id_number: function(frm) {
        frm.set_value('id_no', frm.doc.id_number);
    }

});

frappe.ui.form.on('Customer', {
    id_expiry: function(frm) {
        frm.set_value('id_expiry_2', frm.doc.id_expiry);
    }
});

frappe.ui.form.on('Customer', {
    passport_number: function(frm) {
        frm.set_value('passport_no', frm.doc.passport_number);
    }
});

frappe.ui.form.on('Customer', {
    passport_expiry: function(frm) {
        frm.set_value('passport_expiry_2', frm.doc.passport_expiry);
    }
});
frappe.ui.form.on('Customer', {
    license_expiry: function(frm) {
        frm.set_value('license_expiry_2', frm.doc.license_expiry);
    }
});
frappe.ui.form.on('Customer', {
    license_number: function(frm) {
        frm.set_value('license_no', frm.doc.license_number);
    }
});
