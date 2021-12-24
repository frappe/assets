# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from assets.controllers.base_asset import BaseAsset, get_finance_books
from frappe.model.naming import make_autoname


class AssetSerialNo(BaseAsset):
	pass

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
