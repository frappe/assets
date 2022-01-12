# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from assets.controllers.base_asset import BaseAsset, get_finance_books


class AssetSerialNo(BaseAsset):
	def validate(self):
		super().validate()
		self.validate_asset()

	def before_submit(self):
		super().before_submit()
		self.validate_location()

	def validate_asset(self):
		is_serialized_asset = frappe.db.get_value('Asset_', self.asset, 'is_serialized_asset')

		if not is_serialized_asset:
			frappe.throw(_("{0} is not a Serialized Asset")
				.format(frappe.bold(self.asset)), title=_("Invalid Asset"))

	def validate_location(self):
		if not self.location:
			frappe.throw(_("Please enter Location"), title=_("Missing Field"))

def create_asset_serial_no_docs(asset):
	finance_books = []
	if asset.calculate_depreciation:
		finance_books = get_finance_books(asset.asset_category)

	asset_value = asset.get_initial_asset_value()

	for i in range(asset.num_of_assets):
		serial_no = frappe.get_doc({
			"doctype": "Asset Serial No",
			"asset": asset.name,
			"serial_no": get_serial_no(asset.name, i),
			"asset_value": asset_value,
			"finance_books": finance_books
		})
		serial_no.save(ignore_permissions=True)

def get_serial_no(asset_name, num_of_assets_created):
	return asset_name + "-" + str(num_of_assets_created + 1)