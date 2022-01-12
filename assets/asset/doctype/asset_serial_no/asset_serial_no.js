// Copyright (c) 2021, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Serial No', {
	onload: function(frm) {
		frm.set_query("asset", function() {
			return {
				"filters": {
					"is_serialized_asset": 1
				}
			};
		});
	},

	refresh: function(frm) {
		frm.trigger('toggle_depreciation_fields');
	},

	asset: (frm) => {
		frm.trigger('toggle_depreciation_fields');
	},

	toggle_depreciation_fields: (frm) => {
		if (frm.doc.asset) {
			frappe.db.get_doc('Asset_', frm.doc.asset).then(asset_doc => {
				if (asset_doc.calculate_depreciation) {
					frm.set_df_property('available_for_use_date', 'read_only', 0);
					frm.set_df_property('finance_books', 'read_only', 0);
					frm.toggle_reqd('available_for_use_date', 1);
					frm.toggle_reqd('finance_books', 1);
				}
				else {
					frm.set_df_property('available_for_use_date', 'read_only', 1);
					frm.set_df_property('finance_books', 'read_only', 1);
					frm.toggle_reqd('available_for_use_date', 0);
					frm.toggle_reqd('finance_books', 0);
				}
			});
		} else {
			frm.set_df_property('available_for_use_date', 'read_only', 1);
			frm.set_df_property('finance_books', 'read_only', 1);
			frm.toggle_reqd('available_for_use_date', 0);
			frm.toggle_reqd('finance_books', 0);
		}
	},
});
