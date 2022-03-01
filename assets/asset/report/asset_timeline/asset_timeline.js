// Copyright (c) 2022, Ganga Manoj and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Asset Timeline"] = {
	"filters": [
		{
			fieldname:"asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Asset_",
			reqd: 1,
			on_change: function(query_report) {
				frappe.query_report.set_filter_value({
					serial_no: ""
				});
			}
		},
		{
			fieldname:"serial_no",
			label: __("Serial No"),
			fieldtype: "Link",
			options: "Asset Serial No",
			get_query: () => {
				var asset = frappe.query_report.get_filter_value('asset');
				return {
					filters: {
						'asset': asset
					}
				};
			}
		},
	]
};
