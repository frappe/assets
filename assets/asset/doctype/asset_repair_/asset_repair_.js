// Copyright (c) 2021, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Repair_', {
	setup: function(frm) {
		frm.fields_dict.cost_center.get_query = function(doc) {
			return {
				filters: {
					'is_group': 0,
					'company': doc.company
				}
			};
		};

		frm.fields_dict.project.get_query = function(doc) {
			return {
				filters: {
					'company': doc.company
				}
			};
		};

		frm.fields_dict.warehouse.get_query = function(doc) {
			return {
				filters: {
					'is_group': 0,
					'company': doc.company
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
		if (frm.doc.__islocal) {
			frm.trigger("set_serial_no_and_num_of_assets");
		}

		if (frm.doc.docstatus) {
			frm.add_custom_button("View General Ledger", function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name
				};
				frappe.set_route("query-report", "General Ledger");
			});
		}
	},

	repair_status: (frm) => {
		if (frm.doc.completion_date && frm.doc.repair_status == "Completed") {
			frappe.call ({
				method: "assets.asset.doctype.asset_repair_.asset_repair_.get_downtime",
				args: {
					"failure_date":frm.doc.failure_date,
					"completion_date":frm.doc.completion_date
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("downtime", r.message + " Hrs");
					}
				}
			});
		}

		if (frm.doc.repair_status == "Completed") {
			frm.set_value('completion_date', frappe.datetime.now_datetime());
		}
	},

	stock_items_on_form_rendered() {
		erpnext.setup_serial_or_batch_no();
	},

	asset: (frm) => {
		frm.trigger("set_serial_no_and_num_of_assets");
	},

	set_serial_no_and_num_of_assets: (frm) => {
		frappe.db.get_value('Asset_', frm.doc.asset, ['is_serialized_asset', 'num_of_assets'], (r) => {
			if (r && r.is_serialized_asset) {
				frm.set_df_property('serial_no', 'read_only', 0);
				frm.set_df_property('serial_no', 'reqd', 1);

				frm.set_value('num_of_assets', 0);
				frm.set_df_property('num_of_assets', 'hidden', 1);
			} else {
				frm.set_df_property('serial_no', 'read_only', 1);
				frm.set_df_property('serial_no', 'reqd', 0);
				frm.set_value("serial_no", "");

				if (r.num_of_assets > 1) {
					frm.set_value('num_of_assets', r.num_of_assets);
					frm.set_df_property('num_of_assets', 'hidden', 0);
				}
			}
		});
	}
});

frappe.ui.form.on('Asset Repair Consumed Item', {
	qty: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'amount', row.qty * row.rate);
	},
});
