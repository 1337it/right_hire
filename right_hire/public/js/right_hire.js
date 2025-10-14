frappe.provide("right_hire");

right_hire.utils = {
    check_vehicle_availability: function(vehicle, start_datetime, end_datetime, callback) {
        frappe.call({
            method: "right_hire.api.vehicle.check_availability",
            args: {vehicle: vehicle, start_datetime: start_datetime, end_datetime: end_datetime},
            callback: function(r) { if (callback) callback(r.message); }
        });
    }
};

frappe.realtime.on("vehicle_status_changed", function(data) {
    frappe.show_alert({
        message: __("Vehicle {0} status changed to {1}", [data.vehicle, data.status]),
        indicator: 'blue'
    });
});
