// Copyright (c) 2022, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on('Asset Revaluation', {
	setup: function(frm) {
		frm.add_fetch('company', 'cost_center', 'cost_center');

		frm.set_query('cost_center', function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			}
		});
		frm.set_query('asset', function() {
			return {
				filters: {
					docstatus: 1
				}
			};
		});
	},

	onload: function(frm) {
		if(frm.is_new() && frm.doc.asset) {
			frm.trigger("set_current_asset_value");
		}

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh: function(frm) {
		frm.trigger('toggle_display_based_on_depreciation_and_serialization');
	},

	company: function(frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	asset: (frm) => {
		frm.trigger('toggle_display_based_on_depreciation_and_serialization');
		frm.trigger("set_current_asset_value");
	},

	finance_book: function(frm) {
		frm.trigger("set_current_asset_value");
	},

	toggle_display_based_on_depreciation_and_serialization: (frm) => {
		if (frm.doc.asset) {
			frappe.db.get_value('Asset_', frm.doc.asset, ['is_serialized_asset', 'num_of_assets', 'calculate_depreciation'], (r) => {
				if (r && r.is_serialized_asset) {
					frm.set_df_property('serial_no', 'read_only', 0);
					frm.set_df_property('serial_no', 'reqd', 1);

					frm.set_value('num_of_assets', 0);
					frm.set_df_property('num_of_assets', 'hidden', 1);
					frm.set_df_property('num_of_assets', 'reqd', 0);
				} else {
					frm.set_df_property('serial_no', 'read_only', 1);
					frm.set_df_property('serial_no', 'reqd', 0);
					frm.set_value('serial_no', '');

					if (r.num_of_assets > 1) {
						frm.set_value('num_of_assets', r.num_of_assets);
						frm.set_df_property('num_of_assets', 'hidden', 0);
						frm.set_df_property('num_of_assets', 'reqd', 1);
					} else {
						frm.set_df_property('num_of_assets', 'reqd', 0);
					}
				}

				if (r.calculate_depreciation) {
					frm.set_df_property('finance_book', 'hidden', 0);
				} else {
					frm.set_df_property('finance_book', 'hidden', 1);
				}
			});
		} else {
			frm.set_df_property('serial_no', 'hidden', 1);
			frm.set_df_property('num_of_assets', 'hidden', 1);
			frm.set_df_property('finance_book', 'hidden', 1);
		}
	},

	num_of_assets: (frm) => {
		frappe.db.get_value('Asset_', frm.doc.asset, ['is_serialized_asset', 'num_of_assets'], (r) => {
			if (r && !r.is_serialized_asset) {
				if (frm.doc.num_of_assets < r.num_of_assets) {
					frappe.msgprint({
						title: __('Warning'),
						message: __('Asset {0} will be split on submitting this repair as the Number of Assets entered \
							is less than {1}.', [frm.doc.asset, r.num_of_assets])
					});
				}
			}
		})
	},

	set_current_asset_value: function(frm) {
		if (frm.doc.asset) {
			frm.call({
				method: "get_current_asset_value",
				args: {
					asset: frm.doc.asset,
					serial_no: frm.doc.serial_no,
					finance_book: frm.doc.finance_book
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('current_asset_value', r.message);
					}
				}
			});
		}
	}
});
