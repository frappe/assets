// Copyright (c) 2021, Ganga Manoj and contributors
// For license information, please see license.txt

frappe.ui.form.on('Depreciation Schedule_', {
	refresh: function(frm) {
		if (frm.doc.status == "Active") {
			frm.add_custom_button(__("Post Depreciation Entries"), function() {
				frm.trigger("post_depreciation_entries");
			});
		}
	},

	post_depreciation_entries: function(frm) {

	}
});
