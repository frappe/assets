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
});
