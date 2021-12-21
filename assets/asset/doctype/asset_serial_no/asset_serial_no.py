# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

from assets.asset.doctype.asset_.asset_ import get_finance_books


class AssetSerialNo(Document):
	def on_submit(self):
		self.record_asset_purchase_creation_and_receipt()

	def record_asset_purchase_creation_and_receipt(self):
		asset = frappe.get_doc("Asset_", self.asset)

		asset.record_asset_purchase(self.serial_no)
		asset.record_asset_creation(self)
		asset.record_asset_receipt(self.serial_no)

def create_asset_serial_no_docs(asset):
	finance_books = []
	if asset.calculate_depreciation:
		finance_books = get_finance_books(asset.asset_category)

	asset_value = asset.get_initial_asset_value()

	for _ in range(asset.num_of_assets):
		serial_no = frappe.get_doc({
			"doctype": "Asset Serial No",
			"asset": asset.name,
			"serial_no": make_autoname(asset.serial_no_naming_series),
			"asset_value": asset_value,
			"finance_books": finance_books
		})
		serial_no.save()
