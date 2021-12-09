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

	item_code: function(frm) {
		if(frm.doc.item_code) {
			frm.trigger('set_finance_book');
		}
	},

	set_finance_book: function(frm) {
		frappe.call({
			method: "assets.asset.doctype.asset_.asset_.get_finance_books",
			args: {
				asset_category: frm.doc.asset_category
			},
			callback: function(r) {
				if(r.message) {
					frm.set_value('finance_books', r.message);
				}
			}
		})
	},

	purchase_receipt: (frm) => {
		frm.trigger('toggle_reference_doc');
		if (frm.doc.purchase_receipt) {
			if (frm.doc.item_code) {
				frappe.db.get_doc('Purchase Receipt', frm.doc.purchase_receipt).then(pr_doc => {
					frm.events.set_values_from_purchase_doc(frm, 'Purchase Receipt', pr_doc)
				});
			} else {
				frm.set_value('purchase_receipt', '');
				frappe.msgprint({
					title: __('Not Allowed'),
					message: __("Please select Item Code first")
				});
			}
		}
	},

	purchase_invoice: (frm) => {
		frm.trigger('toggle_reference_doc');
		if (frm.doc.purchase_invoice) {
			if (frm.doc.item_code) {
				frappe.db.get_doc('Purchase Invoice', frm.doc.purchase_invoice).then(pi_doc => {
					frm.events.set_values_from_purchase_doc(frm, 'Purchase Invoice', pi_doc)
				});
			} else {
				frm.set_value('purchase_invoice', '');
				frappe.msgprint({
					title: __('Not Allowed'),
					message: __("Please select Item Code first")
				});
			}
		}
	},

	set_values_from_purchase_doc: function(frm, doctype, purchase_doc) {
		frm.set_value('company', purchase_doc.company);
		frm.set_value('purchase_date', purchase_doc.posting_date);
		const item = purchase_doc.items.find(item => item.item_code === frm.doc.item_code);
		if (!item) {
			doctype_field = frappe.scrub(doctype)
			frm.set_value(doctype_field, '');
			frappe.msgprint({
				title: __('Invalid {0}', [__(doctype)]),
				message: __('The selected {0} does not contain the selected Asset Item.', [__(doctype)]),
				indicator: 'red'
			});
		}
		frm.set_value('gross_purchase_amount', item.base_net_rate + item.item_tax_amount);
		frm.set_value('purchase_receipt_amount', item.base_net_rate + item.item_tax_amount);
		item.asset_location && frm.set_value('location', item.asset_location);
		frm.set_value('cost_center', item.cost_center || purchase_doc.cost_center);
	},
});
