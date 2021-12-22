# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document

class AssetRepair_(Document):
	def validate(self):
		self.asset_doc = frappe.get_doc('Asset_', self.asset)
		self.update_status()

		if self.get('items'):
			self.set_total_value()

	def update_status(self):
		if self.repair_status == 'Pending':
			frappe.db.set_value('Asset_', self.asset, 'status', 'Out of Order')
		else:
			self.asset_doc.set_status()

	def set_total_value(self):
		for item in self.get('items'):
			item.amount = flt(item.rate) * flt(item.qty)
