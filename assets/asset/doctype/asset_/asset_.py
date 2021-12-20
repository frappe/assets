# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import (
	cint,
	flt,
	getdate,
	get_datetime,
	nowdate,
)
from erpnext.controllers.accounts_controller import AccountsController
from assets.asset.doctype.asset_activity.asset_activity import create_asset_activity


class Asset_(AccountsController):
	def validate(self):
		self.validate_asset_values()
		self.validate_item()
		self.set_missing_values()

		if not self.is_serialized_asset:
			self.status = self.get_status()

	def on_submit(self):
		if self.is_serialized_asset:
			from assets.asset.doctype.asset_serial_no.asset_serial_no import create_asset_serial_no_docs

			create_asset_serial_no_docs(self)
		else:
			if self.calculate_depreciation:
				self.validate_depreciation_posting_start_date()

			self.record_asset_receipt()
			self.record_asset_creation()
			self.record_asset_purchase()
			self.set_status()

	def validate_asset_values(self):
		self.validate_purchase_document()
		self.validate_number_of_assets()

		if self.is_serialized_asset:
			self.validate_serial_number_naming_series()
		elif self.calculate_depreciation:
			self.validate_available_for_use_date()

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

	def validate_number_of_assets(self):
		if self.num_of_assets <= 0:
			frappe.throw(_("Number of Assets needs to be greater than zero."))

	def validate_serial_number_naming_series(self):
		naming_series = self.get('serial_no_naming_series')

		if "#" in naming_series and "." not in naming_series:
			frappe.throw(_("Please add a ' . ' before the '#'s in the Serial Number Naming Series."),
				title=_("Invalid Naming Series"))

	def validate_available_for_use_date(self):
		if self.available_for_use_date and getdate(self.available_for_use_date) < getdate(self.purchase_date):
			frappe.throw(_("Available-for-use Date should be after purchase date"))

	def validate_depreciation_posting_start_date(self):
		for finance_book in self.finance_books:
			if finance_book.depreciation_posting_start_date == self.available_for_use_date:
				frappe.throw(_("Row #{}: Depreciation Posting Date should not be equal to Available for Use Date.")
					.format(finance_book.idx), title=_("Incorrect Date"))

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

	def set_missing_values(self):
		if not self.asset_category:
			self.asset_category = frappe.get_cached_value("Item", self.item_code, "asset_category")

		if not self.get('finance_books'):
			finance_books = get_finance_books(self.asset_category)
			self.set('finance_books', finance_books)

		if not self.is_serialized_asset:
			self.set_initial_asset_value()

	def set_initial_asset_value(self):
		self.asset_value = self.get_initial_asset_value()

	def get_initial_asset_value(self):
		if self.calculate_depreciation and self.is_existing_asset:
			asset_value = self.gross_purchase_amount - self.opening_accumulated_depreciation
		else:
			asset_value = self.gross_purchase_amount

		return asset_value

	def set_status(self, status=None):
		if not status:
			status = self.get_status()

		self.db_set("status", status)

	def get_status(self):
		if self.docstatus == 0:
			status = "Draft"

		elif self.docstatus == 1:
			status = "Submitted"

			if self.journal_entry_for_scrap:
				status = "Scrapped"
			elif self.finance_books:
				idx = self.get_default_finance_book_idx() or 0

				expected_value_after_useful_life = self.finance_books[idx].expected_value_after_useful_life
				value_after_depreciation = self.finance_books[idx].value_after_depreciation

				if flt(value_after_depreciation) <= expected_value_after_useful_life:
					status = "Fully Depreciated"
				elif flt(value_after_depreciation) < flt(self.gross_purchase_amount):
					status = 'Partially Depreciated'

		elif self.docstatus == 2:
			status = "Cancelled"

		return status

	def get_default_finance_book_idx(self):
		if not self.get('default_finance_book') and self.company:
			self.default_finance_book = get_default_finance_book(self.company)

		if self.get('default_finance_book'):
			for finance_book in self.get('finance_books'):
				if finance_book.finance_book == self.default_finance_book:
					return cint(finance_book.idx) - 1

	def record_asset_receipt(self):
		reference_doctype, reference_docname = self.get_purchase_details()
		transaction_date = getdate(self.purchase_date)

		if reference_docname:
			posting_date, posting_time = frappe.db.get_value(
				reference_doctype, reference_docname, ["posting_date", "posting_time"]
			)
			transaction_date = get_datetime("{} {}".format(posting_date, posting_time))

		assets = [{
			'asset': self.name,
			'asset_name': self.asset_name,
			'target_location': self.location,
			'to_employee': self.custodian
		}]

		asset_movement = frappe.get_doc({
			'doctype': 'Asset Movement_',
			'assets': assets,
			'purpose': 'Receipt',
			'company': self.company,
			'transaction_date': transaction_date,
			'reference_doctype': reference_doctype,
			'reference_name': reference_docname
		}).insert()
		asset_movement.submit()

	def record_asset_purchase(self):
		purchase_doctype, purchase_docname = self.get_purchase_details()

		create_asset_activity(
			asset = self.name,
			activity_type = 'Purchase',
			reference_doctype = purchase_doctype,
			reference_docname = purchase_docname,
			activity_date = self.purchase_date
		)

	def record_asset_creation(self):
		create_asset_activity(
			asset = self.name,
			activity_type = 'Creation',
			reference_doctype = self.doctype,
			reference_docname = self.name
		)

	def get_purchase_details(self):
		purchase_doctype = 'Purchase Receipt' if self.purchase_receipt else 'Purchase Invoice'
		purchase_docname = self.purchase_receipt or self.purchase_invoice

		return purchase_doctype, purchase_docname

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

def get_default_finance_book(company=None):
	from erpnext import get_default_company

	if not company:
		company = get_default_company()

	if not hasattr(frappe.local, 'default_finance_book'):
		frappe.local.default_finance_book = {}

	if not company in frappe.local.default_finance_book:
		frappe.local.default_finance_book[company] = frappe.get_cached_value('Company',
			company,  "default_finance_book")

	return frappe.local.default_finance_book[company]