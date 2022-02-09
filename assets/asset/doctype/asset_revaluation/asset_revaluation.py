# Copyright (c) 2022, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, formatdate

from assets.asset.doctype.asset_repair_.asset_repair_ import (
	validate_num_of_assets,
	validate_serial_no
)

class AssetRevaluation(Document):
	def validate(self):
		self.validate_asset_values()
		self.set_current_asset_value()

	def validate_asset_values(self):
		purchase_date, is_serialized_asset, num_of_assets = frappe.db.get_value(
			"Asset_",
			self.asset,
			["purchase_date", "is_serialized_asset", "num_of_assets"]
		)

		self.validate_transaction_date_against_purchase_date(purchase_date)

		if is_serialized_asset:
			validate_serial_no(self)
		else:
			validate_num_of_assets(self, num_of_assets)

	def validate_transaction_date_against_purchase_date(self, purchase_date):
		if getdate(self.date) < getdate(purchase_date):
			frappe.throw(_("Asset Revaluation cannot be posted before Asset's purchase date: <b>{0}</b>.")
				.format(formatdate(purchase_date)), title = "Invalid Date")

	def set_current_asset_value(self):
		if not self.current_asset_value and self.asset:
			self.current_asset_value = get_current_asset_value(self.asset, self.serial_no, self.finance_book)

@frappe.whitelist()
def get_current_asset_value(asset, serial_no=None, finance_book=None):
	if not finance_book:
		if serial_no:
			return frappe.db.get_value("Asset Serial No", serial_no, "asset_value")
		else:
			return frappe.db.get_value("Asset_", asset, "asset_value")

	else:
		if serial_no:
			parent = serial_no
			parent_type = "Asset Serial No"
		else:
			parent = asset
			parent_type = "Asset_"

		filters = {
			"parent": parent,
			"parenttype": parent_type,
			"finance_book": finance_book
		}

		return frappe.db.get_value("Asset Finance Book", filters, "asset_value")