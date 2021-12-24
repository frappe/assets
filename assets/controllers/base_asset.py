# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, getdate, get_datetime
from frappe.model.document import Document

from assets.asset.doctype.asset_activity.asset_activity import create_asset_activity
from assets.asset.doctype.asset_category_.asset_category_ import get_asset_category_account


class BaseAsset(Document):
	def validate(self):
		self.validate_number_of_assets()
		self.set_missing_values()

		if self.is_not_serialized_asset():
			if self.is_depreciable_asset():
				self.validate_available_for_use_date()

			self.status = self.get_status()

	def before_submit(self):
		if self.is_not_serialized_asset():
			if self.is_depreciable_asset():
				self.validate_depreciation_posting_start_date()

			self.record_asset_purchase()
			self.record_asset_creation()
			self.record_asset_receipt()
			self.set_status()

	def is_not_serialized_asset(self):
		"""
			Certain actions should only be performed on Asset Serial No docs or non-serialized Assets.
		"""
		if self.doctype == "Asset Serial No" or self.is_serialized_asset:
			return False

		return True

	def is_depreciable_asset(self):
		if self.doctype == "Asset_":
			return self.calculate_depreciation
		else:
			return frappe.db.get_value("Asset_", self.asset, "calculate_depreciation")

	def validate_number_of_assets(self):
		if self.doctype == "Asset_" and self.num_of_assets <= 0:
			frappe.throw(_("Number of Assets needs to be greater than zero."))

		purchase_doctype, purchase_docname = self.get_purchase_details()

		if purchase_docname:
			num_of_items_in_purchase_doc = self.get_num_of_items_in_purchase_doc(purchase_doctype, purchase_docname)
			num_of_assets_already_created = self.get_num_of_assets_already_created(purchase_doctype, purchase_docname)
			num_of_assets = self.get_num_of_assets_in_this_group()

			self.validate_num_of_assets_purchased(num_of_assets, num_of_items_in_purchase_doc, purchase_docname)
			self.validate_total_num_of_assets(num_of_assets, num_of_assets_already_created,
				num_of_items_in_purchase_doc, purchase_docname)

	def get_purchase_details(self):
		if self.doctype == "Asset_":
			purchase_receipt, purchase_invoice = self.purchase_receipt, self.purchase_invoice
		else:
			purchase_receipt, purchase_invoice = frappe.db.get_value(
				"Asset_",
				self.asset,
				["purchase_receipt", "purchase_invoice"]
			)

		purchase_doctype = 'Purchase Receipt' if purchase_receipt else 'Purchase Invoice'
		purchase_docname = purchase_receipt or purchase_invoice

		return purchase_doctype, purchase_docname

	def get_num_of_items_in_purchase_doc(self, purchase_doctype, purchase_docname):
		items_doctype = purchase_doctype + " Item"
		item = self.get_item()

		num_of_items_in_purchase_doc = frappe.db.get_value(
			items_doctype,
			{
				"parent": purchase_docname,
				"item_code": item
			},
			"qty"
		)
		return num_of_items_in_purchase_doc

	def get_item(self):
		if self.doctype == "Asset_":
			return self.item_code
		else:
			return frappe.db.get_value("Asset_", self.asset, "item_code")

	def get_num_of_assets_already_created(self, purchase_doctype, purchase_docname):
		purchase_doctype = "purchase_receipt" if purchase_doctype == "Purchase Receipt" else "purchase_invoice"
		asset_name = self.name if self.doctype == "Asset_" else self.asset

		num_of_assets_already_created = frappe.db.get_all(
			"Asset_",
			filters = {
				purchase_doctype: purchase_docname,
				"name": ["!=", asset_name]
			},
			pluck = "num_of_assets"
		)
		num_of_assets_already_created = sum(num_of_assets_already_created)

		return num_of_assets_already_created

	def get_num_of_assets_in_this_group(self):
		if self.doctype == "Asset_":
			return self.num_of_assets
		else:
			return frappe.db.get_value("Asset_", self.asset, "num_of_assets")

	def validate_num_of_assets_purchased(self, num_of_assets, num_of_items_in_purchase_doc, purchase_docname):
		if num_of_assets > num_of_items_in_purchase_doc:
			frappe.throw(_("Number of Assets cannot be greater than the qty of {0} purchased in {1}, \
				which is {2}.").format(frappe.bold(self.item_code), frappe.bold(purchase_docname),
				frappe.bold(int(num_of_items_in_purchase_doc))))

	def validate_total_num_of_assets(self, num_of_assets, num_of_assets_already_created, num_of_items_in_purchase_doc, purchase_docname):
		if (num_of_assets_already_created + num_of_assets) > num_of_items_in_purchase_doc:
			max_num_of_assets = num_of_items_in_purchase_doc - num_of_assets_already_created

			frappe.throw(_("The Number of Assets to be created needs to be decreased. \
				A maximum of {0} Assets can be created now, as only {1} were purchased in {2}, \
				of which {3} have already been created.")
				.format(frappe.bold(int(max_num_of_assets)), frappe.bold(int(num_of_items_in_purchase_doc)),
				frappe.bold(purchase_docname), frappe.bold(int(num_of_assets_already_created))),
				title=_("Number of Assets Exceeded Limit"))

	def set_missing_values(self):
		if not self.get('finance_books'):
			asset_category = self.get_asset_category()
			finance_books = get_finance_books(asset_category)
			self.set('finance_books', finance_books)

		if not self.get('asset_value') and self.is_not_serialized_asset():
			self.set_initial_asset_value()

	def get_asset_category(self):
		if self.doctype == "Asset_":
			if not self.get('asset_category'):
				asset_category = frappe.get_cached_value("Item", self.item_code, "asset_category")
				self.set_asset_category(asset_category)
				return asset_category
			else:
				return self.asset_category
		else:
			return frappe.get_value("Asset_", self.asset, "asset_category")

	def set_asset_category(self, asset_category):
		self.asset_category = asset_category

	def set_initial_asset_value(self):
		self.asset_value = self.get_initial_asset_value()

	def get_initial_asset_value(self):
		purchase_doc = self.get_purchase_details()
		gross_purchase_amount, opening_accumulated_depreciation = self.get_gross_purchase_amount_and_opening_accumulated_depreciation()

		if self.is_depreciable_asset() and not purchase_doc:
			asset_value = gross_purchase_amount - opening_accumulated_depreciation
		else:
			asset_value = gross_purchase_amount

		return asset_value

	def get_gross_purchase_amount_and_opening_accumulated_depreciation(self):
		if self.doctype == "Asset_":
			return self.gross_purchase_amount, self.opening_accumulated_depreciation
		else:
			return frappe.db.get_value("Asset_", self.asset, ["gross_purchase_amount", "opening_accumulated_depreciation"])

	def validate_available_for_use_date(self):
		purchase_date = self.get_purchase_date()

		if self.available_for_use_date and getdate(self.available_for_use_date) < getdate(purchase_date):
			frappe.throw(_("Available-for-use Date should be after purchase date"))

	def get_purchase_date(self):
		if self.doctype == "Asset_":
			return self.purchase_date
		else:
			return frappe.db.get_value("Asset_", self.asset, "purchase_date")

	def validate_depreciation_posting_start_date(self):
		for finance_book in self.finance_books:
			if finance_book.depreciation_posting_start_date == self.available_for_use_date:
				frappe.throw(_("Row #{}: Depreciation Posting Date should not be equal to Available for Use Date.")
					.format(finance_book.idx), title=_("Incorrect Date"))

	def record_asset_purchase(self):
		purchase_doctype, purchase_docname = self.get_purchase_details()
		serial_no = self.get_serial_no()

		create_asset_activity(
			asset = self.name,
			asset_serial_no = serial_no,
			activity_type = 'Purchase',
			reference_doctype = purchase_doctype,
			reference_docname = purchase_docname,
			activity_date = self.get_purchase_date()
		)

	def record_asset_creation(self):
		create_asset_activity(
			asset = self.name,
			activity_type = 'Creation',
			reference_doctype = self.doctype,
			reference_docname = self.name
		)

	def record_asset_receipt(self):
		reference_doctype, reference_docname = self.get_purchase_details()
		transaction_date = getdate(self.get_purchase_date())
		serial_no = self.get_serial_no()

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
			'serial_no': serial_no,
			'purpose': 'Receipt',
			'company': self.company,
			'transaction_date': transaction_date,
			'reference_doctype': reference_doctype,
			'reference_name': reference_docname
		}).insert()
		asset_movement.submit()

	def get_serial_no(self):
		if self.doctype == "Asset_":
			return None
		else:
			return self.serial_no

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

def get_asset_account(account_name, asset=None, asset_category=None, company=None):
	account = None
	if asset:
		account = get_asset_category_account(account_name, asset=asset,
				asset_category = asset_category, company = company)

	if not asset and not account:
		account = get_asset_category_account(account_name, asset_category = asset_category, company = company)

	if not account:
		account = frappe.get_cached_value('Company',  company,  account_name)

	if not account:
		if not asset_category:
			frappe.throw(_("Set {0} in company {1}").format(account_name.replace('_', ' ').title(), company))
		else:
			frappe.throw(_("Set {0} in asset category {1} or company {2}")
				.format(account_name.replace('_', ' ').title(), asset_category, company))

	return account

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

@frappe.whitelist()
def make_asset_movement(assets, purpose=None):
	import json

	if isinstance(assets, str):
		assets = json.loads(assets)

	if len(assets) == 0:
		frappe.throw(_('Atleast one asset has to be selected.'))

	asset_movement = frappe.new_doc("Asset Movement")
	asset_movement.quantity = len(assets)
	asset_movement.purpose = purpose

	for asset in assets:
		asset = frappe.get_doc('Asset', asset.get('name'))
		asset_movement.company = asset.get('company')
		asset_movement.append("assets", {
			'asset': asset.get('name'),
			'source_location': asset.get('location'),
			'from_employee': asset.get('custodian')
		})

	if asset_movement.get('assets'):
		return asset_movement.as_dict()
