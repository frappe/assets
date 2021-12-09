# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import (
	cint,
	getdate,
	nowdate,
)
from erpnext.controllers.accounts_controller import AccountsController


class Asset_(AccountsController):
	def validate(self):
		self.validate_asset_values()

	def validate_asset_values(self):
		self.validate_purchase_document()
		self.validate_available_for_use_date()

	def validate_purchase_document(self):
		if (is_cwip_accounting_enabled(self.asset_category)
			and not self.purchase_receipt
			and self.purchase_invoice
			and not frappe.db.get_value('Purchase Invoice', self.purchase_invoice, 'update_stock')):
			frappe.throw(_("Update stock must be enable for the purchase invoice {0}").format(self.purchase_invoice))

	def validate_available_for_use_date(self):
		if self.available_for_use_date and getdate(self.available_for_use_date) < getdate(self.purchase_date):
			frappe.throw(_("Available-for-use Date should be after purchase date"))

@frappe.whitelist()
def get_finance_books(asset_category):
	asset_category_doc = frappe.get_doc('Asset Category_', asset_category)
	books = []
	for d in asset_category_doc.finance_books:
		books.append({
			'finance_book': d.finance_book,
			'depreciation_posting_start_date': nowdate()
		})

	return books

def is_cwip_accounting_enabled(asset_category):
	return cint(frappe.db.get_value("Asset Category", asset_category, "enable_cwip_accounting"))
