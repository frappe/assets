// Copyright (c) 2021, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts.dimensions");

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

		if (frm.doc.docstatus == 1) {
			if (frm.doc.is_serialized_asset) {
				frm.trigger("toggle_display_create_serial_nos_button");
			}
			else {
				if (in_list(["Submitted", "Partially Depreciated", "Fully Depreciated"], frm.doc.status)) {
					frm.add_custom_button(__("Transfer Asset"), function() {
						erpnext.asset.transfer_asset(frm);
					}, __("Manage"));

					frm.add_custom_button(__("Scrap Asset"), function() {
						erpnext.asset.scrap_asset(frm);
					}, __("Manage"));

					frm.add_custom_button(__("Sell Asset"), function() {
						frm.trigger("make_sales_invoice");
					}, __("Manage"));
				}
				else if (frm.doc.status=='Scrapped') {
					frm.add_custom_button(__("Restore Asset"), function() {
						erpnext.asset.restore_asset(frm);
					}, __("Manage"));
				}

				if (frm.doc.maintenance_required && !frm.doc.maintenance_schedule) {
					frm.add_custom_button(__("Maintain Asset"), function() {
						frm.trigger("create_asset_maintenance");
					}, __("Manage"));
				}

				frm.add_custom_button(__("Repair Asset"), function() {
					frm.trigger("create_asset_repair");
				}, __("Manage"));

				if (frm.doc.status != 'Fully Depreciated') {
					frm.add_custom_button(__("Adjust Asset Value"), function() {
						frm.trigger("create_asset_value_adjustment");
					}, __("Manage"));
				}

				if (!frm.doc.calculate_depreciation) {
					frm.add_custom_button(__("Create Depreciation Entry"), function() {
						frm.trigger("make_journal_entry");
					}, __("Manage"));
				}

				if (frm.doc.purchase_receipt || !frm.doc.is_existing_asset) {
					frm.add_custom_button(__("View General Ledger"), function() {
						frappe.route_options = {
							"voucher_no": frm.doc.name,
							"from_date": frm.doc.available_for_use_date,
							"to_date": frm.doc.available_for_use_date,
							"company": frm.doc.company
						};
						frappe.set_route("query-report", "General Ledger");
					}, __("Manage"));
				}
			}
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

	toggle_display_create_serial_nos_button: function (frm) {
		if (!frm.doc.is_existing_asset) {
			frappe.call({
				method: "assets.controllers.base_asset.get_purchase_details",
				args: {
					asset: frm.doc
				},
				callback: function(r) {
					if(r.message) {
						frappe.call({
							method: "assets.controllers.base_asset.get_num_of_items_in_purchase_doc",
							args: {
								asset: frm.doc,
								purchase_doctype: r.message[0],
								purchase_docname: r.message[1]
							},
							callback: function(r) {
								if(r.message) {
									if (r.message > frm.doc.num_of_assets) {
										frm.add_custom_button(__("Create Serial Numbers"), function() {
											frm.trigger("create_asset_serial_nos");
										});
									}
								}
							}
						})
					}
				}
			})
		} else {
			frm.add_custom_button(__("Create Serial Numbers"), function() {
				frm.trigger("create_asset_serial_nos");
			});
		}
	},

	create_asset_serial_nos: function(frm) {

	},

	make_sales_invoice: function(frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"item_code": frm.doc.item_code,
				"company": frm.doc.company
			},
			method: "assets.controllers.base_asset.make_sales_invoice",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		})
	},

	create_asset_maintenance: function(frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"item_code": frm.doc.item_code,
				"item_name": frm.doc.item_name,
				"asset_category": frm.doc.asset_category,
				"company": frm.doc.company
			},
			method: "assets.controllers.base_asset.create_asset_maintenance",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		})
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
			method: "assets.controllers.base_asset.get_finance_books",
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
