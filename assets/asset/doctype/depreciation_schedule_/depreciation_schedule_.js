// Copyright (c) 2021, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.ui.form.on('Depreciation Schedule_', {
	setup: function(frm) {
		frm.fields_dict.serial_no.get_query = function(doc) {
			return {
				filters: {
					'asset': doc.asset
				}
			};
		};
	},

	refresh: function(frm) {
		if (frm.doc.status == "Active") {
			frm.add_custom_button(__("Post Depreciation Entries"), function() {
				frm.trigger("post_depreciation_entries");
			});
		}
	},

	post_depreciation_entries: function(frm) {

	},

	asset: (frm) => {
		frappe.db.get_value('Asset_', frm.doc.asset, 'is_serialized_asset', (r) => {
			if (r && r.is_serialized_asset) {
				frm.set_df_property('serial_no', 'read_only', 0);
				frm.set_df_property('serial_no', 'reqd', 1);
			} else {
				frm.set_df_property('serial_no', 'read_only', 1);
				frm.set_df_property('serial_no', 'reqd', 0);
				frm.set_value("serial_no", "");
			}
		});
	}
});
