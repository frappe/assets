# Copyright (c) 2022, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, formatdate, flt

from assets.asset.doctype.asset_repair_.asset_repair_ import (
	validate_num_of_assets,
	validate_serial_no
)
from assets.asset.doctype.depreciation_schedule_.depreciation_posting import (
	get_depreciation_accounts,
	get_depreciation_details,
	add_accounting_dimensions
)

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)

class AssetRevaluation(Document):
	def validate(self):
		self.validate_asset_values()
		self.set_current_asset_value()
		self.set_difference_amount()

	def on_submit(self):
		if self.current_asset_value > self.new_asset_value:
			self.make_depreciation_entry()

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

	def set_difference_amount(self):
		self.difference_amount = abs(flt(self.current_asset_value - self.new_asset_value))

	def make_depreciation_entry(self):
		asset = frappe.get_doc("Asset_", self.asset)

		credit_account, debit_account = get_depreciation_accounts(asset.asset_category, asset.company)
		depreciation_cost_center, depreciation_series = get_depreciation_details(asset.company)

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Depreciation Entry"
		je.naming_series = depreciation_series
		je.posting_date = self.date
		je.company = self.company
		je.remark = "Depreciation Entry against {0} worth {1}" \
			.format((self.serial_no or self.asset), self.difference_amount)
		je.finance_book = self.finance_book

		credit_entry, debit_entry = self.get_credit_and_debit_entries(
			credit_account, debit_account, depreciation_cost_center, asset)

		je.append("accounts", credit_entry)
		je.append("accounts", debit_entry)

		je.flags.ignore_permissions = True
		je.submit()

		self.db_set("journal_entry", je.name)

	def get_credit_and_debit_entries(self, credit_account, debit_account, depreciation_cost_center, asset):
		credit_entry = {
			"account": credit_account,
			"credit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center
		}

		debit_entry = {
			"account": debit_account,
			"debit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center
		}

		accounting_dimensions = get_checks_for_pl_and_bs_accounts()
		add_accounting_dimensions(accounting_dimensions, credit_entry, debit_entry, asset)

		return credit_entry, debit_entry

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