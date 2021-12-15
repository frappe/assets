# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class AssetMovement_(Document):
	def validate(self):
		self.validate_asset()

	def validate_asset(self):
		for asset in self.assets:
			status, company = frappe.db.get_value("Asset", asset.asset, ["status", "company"])

			if self.purpose == 'Transfer' and status in ("Draft", "Scrapped", "Sold"):
				frappe.throw(_("Row {0}: {1} asset cannot be transferred.").format(asset.idx, status))

			if company != self.company:
				frappe.throw(_("{0} does not belong to company {1}.").format(asset.asset, self.company))

			if not (asset.source_location or asset.target_location or asset.from_employee or asset.to_employee):
				frappe.throw(_("Either location or employee must be entered."))