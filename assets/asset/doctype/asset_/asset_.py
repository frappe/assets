# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint

from assets.asset.doctype.asset_activity.asset_activity import create_asset_activity
from assets.controllers.base_asset import BaseAsset


class Asset_(BaseAsset):
	def validate(self):
		super().validate()

		self.validate_asset_values()
		self.validate_item()

	def before_submit(self):
		super().before_submit()

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

@frappe.whitelist()
def split_asset(asset, num_of_assets_to_be_separated):
	if isinstance(asset, str):
		asset = frappe.get_doc("Asset_", asset)

	if isinstance(num_of_assets_to_be_separated, str):
		num_of_assets_to_be_separated = int(num_of_assets_to_be_separated)

	validate_num_of_assets_to_be_separated(asset, num_of_assets_to_be_separated)

	new_asset = create_new_asset(asset, num_of_assets_to_be_separated)
	update_existing_asset(asset, num_of_assets_to_be_separated)

	record_asset_split(asset, new_asset, num_of_assets_to_be_separated)
	display_message_on_successfully_splitting_asset(asset, new_asset)

def validate_num_of_assets_to_be_separated(asset, num_of_assets_to_be_separated):
	if num_of_assets_to_be_separated >= asset.num_of_assets:
		frappe.throw(_("Number of Assets to be Separated should be less than the total Number of Assets, which is {0}.")
			.format(frappe.bold(asset.num_of_assets)), title=_("Invalid Number"))

def create_new_asset(asset, num_of_assets_to_be_separated):
	new_asset = frappe.copy_doc(asset)
	new_asset.num_of_assets = num_of_assets_to_be_separated
	new_asset.flags.split_asset = True
	new_asset.submit()
	new_asset.flags.split_asset = False

	return new_asset

def update_existing_asset(asset, num_of_assets_to_be_separated):
	asset.flags.ignore_validate_update_after_submit = True
	asset.num_of_assets -= num_of_assets_to_be_separated
	asset.save()

def record_asset_split(asset, new_asset, num_of_assets_to_be_separated):
	split_assets = [asset.name, new_asset.name]
	is_plural = "s" if num_of_assets_to_be_separated > 1 else ""

	for split_asset in split_assets:
		create_asset_activity(
			asset = split_asset,
			activity_type = 'Split',
			reference_doctype = asset.doctype,
			reference_docname = asset.name,
			notes = _("{0} asset{1} separated from {2} into {3}.")
				.format(num_of_assets_to_be_separated, is_plural, asset.name, new_asset.name)
		)

def display_message_on_successfully_splitting_asset(asset, new_asset):
	new_asset_link = frappe.bold(frappe.utils.get_link_to_form("Asset_", new_asset.name))
	message = _("Asset {0} split successfully. New Asset doc: {1}").format(asset.name, new_asset_link)

	frappe.msgprint(message, title="Sucess", indicator="green")