# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

from assets.asset.doctype.asset_.asset_ import get_finance_books
from assets.asset.doctype.asset_activity.asset_activity import create_asset_activity


class AssetSerialNo(Document):
	def after_save(self):
		self.record_serial_no_creation()

	def record_serial_no_creation(self):
		create_asset_activity(self.asset, "Creation", self.doctype, self.name, self.serial_no)

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
