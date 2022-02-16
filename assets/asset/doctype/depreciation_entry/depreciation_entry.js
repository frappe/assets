// Copyright (c) 2022, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.ui.form.on('Depreciation Entry', {
	setup: function(frm) {
		frm.fields_dict.cost_center.get_query = function(doc) {
			return {
				filters: {
					'is_group': 0,
					'company': doc.company
				}
			};
		};

		frm.fields_dict.asset.get_query = function(doc) {
			return {
				filters: {
					'docstatus': 1
				}
			};
		};

		frm.fields_dict.serial_no.get_query = function(doc) {
			return {
				filters: {
					'asset': doc.asset
				}
			};
		};
	},

	refresh: function(frm) {
		frm.trigger("toggle_display_and_reqd_for_serial_no");
		frm.trigger("toggle_display_for_finance_book");
	},

	asset: (frm) => {
		frm.trigger("toggle_display_and_reqd_for_serial_no");
		frm.trigger("toggle_display_for_finance_book");
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

	toggle_display_for_finance_book: (frm) => {
		if (frm.doc.asset) {
			frappe.db.get_value('Asset_', frm.doc.asset, ['calculate_depreciation'], (r) => {
				if (r && r.calculate_depreciation) {
					if (frm.doc.serial_no) {
						var doctype = 'Asset Serial No';
						var docname = frm.doc.serial_no;
					} else {
						var doctype = 'Asset_';
						var docname = frm.doc.asset;
					}

					frappe.db.get_doc(doctype, docname).then(data => {
						if (data.finance_books.length > 1) {
							frm.set_df_property('finance_book', 'hidden', 0);
							frm.set_df_property('finance_book', 'reqd', 1);
						} else {
							frm.set_df_property('finance_book', 'hidden', 1);
							frm.set_df_property('finance_book', 'reqd', 0);
						}
					})
				} else {
					frm.set_df_property('finance_book', 'hidden', 1);
				}
			})
		} else {
			frm.set_df_property('finance_book', 'hidden', 1);
		}
	}
});
