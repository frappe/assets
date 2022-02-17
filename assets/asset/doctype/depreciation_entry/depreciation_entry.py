# Copyright (c) 2022, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.controllers.accounts_controller import AccountsController

class DepreciationEntry(AccountsController):
	def validate(self):
		self.validate_depreciation_amount()

	def validate_depreciation_amount(self):
		if self.depreciation_amount <= 0:
			frappe.throw(_("Depreciation Amount must be greater than zero."), title = _("Invalid Amount"))

