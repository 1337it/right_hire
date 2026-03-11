frappe.query_reports["Cash Forecast"] = {
	filters: [
		{
			fieldname: "months_ahead",
			label: __("Months Ahead"),
			fieldtype: "Select",
			options: "3\n6\n12\n24\n36",
			default: "12",
			reqd: 1
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "vehicle",
			label: __("Vehicle"),
			fieldtype: "Link",
			options: "Vehicle"
		}
	]
};
