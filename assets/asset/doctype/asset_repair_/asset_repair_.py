# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

class AssetRepair_(Document):
	def validate(self):
		self.asset_doc = frappe.get_doc('Asset_', self.asset)
		self.update_status()

		if self.get('stock_consumption'):
			self.set_total_value()

		self.calculate_total_repair_cost()

	def before_submit(self):
		self.check_repair_status()

	def update_status(self):
		if self.repair_status == 'Pending':
			frappe.db.set_value('Asset_', self.asset, 'status', 'Out of Order')
		else:
			self.asset_doc.set_status()

	def set_total_value(self):
		for item in self.get('items'):
			item.amount = flt(item.rate) * flt(item.qty)

	def calculate_total_repair_cost(self):
		self.total_repair_cost = flt(self.repair_cost)

		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		self.total_repair_cost += total_value_of_stock_consumed

	def get_total_value_of_stock_consumed(self):
		total_value_of_stock_consumed = 0
		if self.get('stock_consumption'):
			for item in self.get('items'):
				total_value_of_stock_consumed += item.amount

		return total_value_of_stock_consumed

	def check_repair_status(self):
		if self.repair_status == "Pending":
			frappe.throw(_("Please update Repair Status."))