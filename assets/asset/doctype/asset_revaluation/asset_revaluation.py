# Copyright (c) 2022, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AssetRevaluation(Document):
	pass

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