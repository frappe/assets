// Copyright (c) 2022, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.ui.form.on('Depreciation Entry', {
	refresh: function(frm) {
		frm.trigger("toggle_display_and_reqd_for_serial_no");
	},

	asset: (frm) => {
		frm.trigger("toggle_display_and_reqd_for_serial_no");
	},

	toggle_display_and_reqd_for_serial_no: (frm) => {
		if (frm.doc.asset) {
			frappe.db.get_value('Asset_', frm.doc.asset, ['is_serialized_asset'], (r) => {
				if (r && r.is_serialized_asset) {
					frm.set_df_property('serial_no', 'hidden', 0);
					frm.set_df_property('serial_no', 'reqd', 1);
				} else {
					frm.set_df_property('serial_no', 'hidden', 1);
					frm.set_df_property('serial_no', 'reqd', 0);
					frm.set_value('serial_no', '');
				}
			});
		} else {
			frm.set_df_property('serial_no', 'hidden', 1);
		}
	},
});
