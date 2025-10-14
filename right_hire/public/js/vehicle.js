frappe.ui.form.on('Vehicle', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('View History'), function() {
                frappe.route_options = {"vehicle": frm.doc.name};
                frappe.set_route("List", "Vehicle Status Log");
            });
        }
    }
});
