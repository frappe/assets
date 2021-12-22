# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

class AssetRepair_(Document):
	def validate(self):
		self.get_asset_doc()
		self.validate_asset()
		self.update_status()

		if self.get('stock_consumption'):
			self.set_total_value()

		self.calculate_total_repair_cost()

	def before_submit(self):
		self.check_repair_status()

		if self.get('stock_consumption') or self.get('capitalize_repair_cost'):
			self.increase_asset_value()

	def get_asset_doc(self):
		if self.get('serial_no'):
			self.asset_doc = frappe.get_doc('Asset Serial No', self.serial_no)
		else:
			self.asset_doc = frappe.get_doc('Asset_', self.asset)

	def validate_asset(self):
		if self.asset_doc.doctype == 'Asset_':
			if self.asset_doc.is_serialized_asset:
				frappe.throw(_("Please enter Serial No as {0} is a Serialized Asset")
					.format(frappe.bold(self.asset)), title=_("Missing Serial No"))

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

	def increase_asset_value(self):
		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()

		if self.asset_doc.calculate_depreciation:
			for row in self.asset_doc.finance_books:
				row.value_after_depreciation += total_value_of_stock_consumed

				if self.capitalize_repair_cost:
					row.value_after_depreciation += self.repair_cost