# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint

from assets.controllers.base_asset import BaseAsset


class Asset_(BaseAsset):
	def validate(self):
		super().validate()

		self.validate_asset_values()
		self.validate_item()

	def on_submit(self):
		if self.is_serialized_asset:
			from assets.asset.doctype.asset_serial_no.asset_serial_no import create_asset_serial_no_docs

			create_asset_serial_no_docs(self)

	def validate_asset_values(self):
		self.validate_purchase_document()

		if self.is_serialized_asset:
			self.validate_serial_number_naming_series()

	def validate_purchase_document(self):
		if self.is_existing_asset:
			if self.purchase_invoice:
				frappe.throw(_("Purchase Invoice cannot be made against an existing asset {0}")
					.format(self.name))

		else:
			purchase_doc = 'Purchase Invoice' if self.purchase_invoice else 'Purchase Receipt'
			purchase_docname = self.purchase_invoice or self.purchase_receipt
			purchase_doc = frappe.get_doc(purchase_doc, purchase_docname)

			if purchase_doc.get('company') != self.company:
				frappe.throw(_("Company of asset {0} and purchase document {1} doesn't match.")
					.format(self.name, purchase_doc.get('name')))

			if (is_cwip_accounting_enabled(self.asset_category)
				and not self.purchase_receipt
				and self.purchase_invoice
				and not frappe.db.get_value('Purchase Invoice', self.purchase_invoice, 'update_stock')):
				frappe.throw(_("Update stock must be enable for the purchase invoice {0}")
					.format(self.purchase_invoice))

	def validate_serial_number_naming_series(self):
		naming_series = self.get('serial_no_naming_series')

		if "#" in naming_series and "." not in naming_series:
			frappe.throw(_("Please add a ' . ' before the '#'s in the Serial Number Naming Series."),
				title=_("Invalid Naming Series"))

	def validate_item(self):
		item = frappe.get_cached_value("Item",
			self.item_code,
			["is_fixed_asset", "is_stock_item", "disabled"],
			as_dict=1)

		if not item:
			frappe.throw(_("Item {0} does not exist").format(self.item_code))
		elif item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))
		elif not item.is_fixed_asset:
			frappe.throw(_("Item {0} must be a Fixed Asset Item").format(self.item_code))
		elif item.is_stock_item:
			frappe.throw(_("Item {0} must be a non-stock item").format(self.item_code))

def is_cwip_accounting_enabled(asset_category):
	return cint(frappe.db.get_value("Asset Category", asset_category, "enable_cwip_accounting"))