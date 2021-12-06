// Copyright (c) 2021, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset_', {
	onload: function(frm) {
		frm.set_query("item_code", function() {
			return {
				"filters": {
					"disabled": 0,
					"is_fixed_asset": 1,
					"is_stock_item": 0
				}
			};
		});

		frm.set_query("department", function() {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	company: function(frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	setup: function(frm) {
		frm.set_query("purchase_receipt", (doc) => {
			return {
				query: "erpnext.controllers.queries.get_purchase_receipts",
				filters: { item_code: doc.item_code }
			}
		});

		frm.set_query("purchase_invoice", (doc) => {
			return {
				query: "erpnext.controllers.queries.get_purchase_invoices",
				filters: { item_code: doc.item_code }
			}
		});
	},

	refresh: function(frm) {
		frm.trigger("toggle_reference_doc");

		if (frm.doc.docstatus == 0) {
			frm.toggle_reqd("finance_books", frm.doc.calculate_depreciation);
		}
	},

	is_existing_asset: function(frm) {
		frm.trigger("toggle_reference_doc");
	},

	toggle_reference_doc: function(frm) {
		if (frm.doc.purchase_receipt && frm.doc.purchase_invoice && frm.doc.docstatus === 1) {
			frm.set_df_property('purchase_invoice', 'read_only', 1);
			frm.set_df_property('purchase_receipt', 'read_only', 1);
		}
		else if (frm.doc.is_existing_asset) {
			frm.toggle_reqd('purchase_receipt', 0);
			frm.toggle_reqd('purchase_invoice', 0);
			frm.toggle_display('purchase_receipt', 0);
 			frm.toggle_display('purchase_invoice', 0);
		}
		else if (frm.doc.purchase_receipt) {
			// if PR is entered, PI is hidden and no longer mandatory
			frm.toggle_reqd('purchase_invoice', 0);
			frm.set_df_property('purchase_invoice', 'read_only', 1);
		}
		else if (frm.doc.purchase_invoice) {
			// if PI is entered, PR  is hidden and no longer mandatory
			frm.toggle_reqd('purchase_receipt', 0);
			frm.set_df_property('purchase_receipt', 'read_only', 1);
		}
		else {
			frm.toggle_reqd('purchase_receipt', 1);
			frm.toggle_reqd('purchase_invoice', 1);
			frm.set_df_property('purchase_receipt', 'read_only', 0);
			frm.set_df_property('purchase_invoice', 'read_only', 0);
			frm.toggle_display('purchase_receipt', 1);
			frm.toggle_display('purchase_invoice', 1);
		}
	},

	calculate_depreciation: function(frm) {
		frm.toggle_reqd("finance_books", frm.doc.calculate_depreciation);
	},
});
