# Copyright (c) 2022, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.controllers.accounts_controller import AccountsController

class DepreciationEntry(AccountsController):
	def validate(self):
		self.validate_depreciation_amount()
		self.validate_reference_doc()
		self.validate_depr_schedule_row()

	def validate_depreciation_amount(self):
		if self.depreciation_amount <= 0:
			frappe.throw(_("Depreciation Amount must be greater than zero."), title = _("Invalid Amount"))

	def validate_reference_doc(self):
		if self.reference_doctype not in ["Asset_", "Asset Serial No", "Depreciation Schedule_"]:
			frappe.throw(_("Reference Document can only be an Asset, Asset Serial No or Depreciation Schedule."),
				title = _("Invalid Reference"))

	def validate_depr_schedule_row(self):
		if self.reference_doctype == "Depreciation Schedule_" and not self.depr_schedule_row:
			frappe.throw(_("Depreciation Schedule Row needs to be fetched."), title = _("Missing Value"))