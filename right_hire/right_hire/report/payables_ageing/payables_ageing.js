frappe.query_reports["Payables Ageing"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "ageing_as_on",
			label: __("Ageing As On"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "ageing_range",
			label: __("Ageing Range (Days)"),
			fieldtype: "Data",
			default: "30,60,90,120",
			description: "Comma-separated day ranges e.g. 30,60,90,120",
		},
	],
};
