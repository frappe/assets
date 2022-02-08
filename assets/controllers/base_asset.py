# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, getdate, get_datetime
from frappe.model.document import Document
import json

from assets.asset.doctype.asset_activity.asset_activity import create_asset_activity
from assets.asset.doctype.asset_category_.asset_category_ import get_asset_category_account
from assets.asset.doctype.depreciation_schedule_.depreciation_schedule_ import (
	create_depreciation_schedules,
	create_schedule_for_finance_book,
	delete_existing_schedules
)


class BaseAsset(Document):
	def validate(self):
		if self.doctype == "Asset Serial No":
			self.get_asset_values()

		self.validate_number_of_assets()
		self.set_missing_values()

		if self.is_not_serialized_asset() and self.is_depreciable_asset():
			self.validate_available_for_use_date()

			if self.is_new():
				self.set_initial_asset_value_for_finance_books()
			else:
				self.create_schedules_if_depr_details_have_been_updated()

		self.status = self.get_status()

	def after_insert(self):
		if self.is_not_serialized_asset() and self.is_depreciable_asset():
			create_depreciation_schedules(self)

	def before_submit(self):
		if self.is_not_serialized_asset():
			if self.is_depreciable_asset():
				self.validate_depreciation_posting_start_date()
				self.submit_depreciation_schedules()

			if not self.flags.split_asset:
				self.record_asset_purchase()
				self.record_asset_creation()
				self.record_asset_receipt()

		self.set_status()

	# to reduce number of db calls
	def get_asset_values(self):
		self.asset_values = frappe.get_value(
			"Asset_",
			self.asset,
			[
				"calculate_depreciation",
				"num_of_assets",
				"asset_category",
				"gross_purchase_amount",
				"opening_accumulated_depreciation",
				"purchase_date",
				"asset_name",
				"company"
			],
			as_dict = 1
		)

	def is_not_serialized_asset(self):
		"""
			Certain actions should only be performed on Asset Serial No docs or non-serialized Assets.
		"""
		if self.doctype == "Asset Serial No" or not self.is_serialized_asset:
			return True

		return False

	def is_depreciable_asset(self):
		if self.doctype == "Asset_":
			return self.calculate_depreciation
		else:
			return self.asset_values["calculate_depreciation"]

	def validate_number_of_assets(self):
		if self.doctype == "Asset_" and self.num_of_assets <= 0:
			frappe.throw(_("Number of Assets needs to be greater than zero."))

		purchase_doctype, purchase_docname = get_purchase_details(self)

		if purchase_docname:
			num_of_items_in_purchase_doc = get_num_of_items_in_purchase_doc(self, purchase_doctype, purchase_docname)
			num_of_assets_already_created = self.get_num_of_assets_already_created(purchase_doctype, purchase_docname)
			num_of_assets = self.get_num_of_assets_in_this_group()

			self.validate_num_of_assets_purchased(num_of_assets, num_of_items_in_purchase_doc, purchase_docname)
			self.validate_total_num_of_assets(num_of_assets, num_of_assets_already_created,
				num_of_items_in_purchase_doc, purchase_docname)

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
			return self.asset_values["num_of_assets"]

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
		if not self.get('asset_value') and self.is_not_serialized_asset():
			self.set_initial_asset_value()

		if self.is_depreciable_asset() and not self.get('finance_books'):
			asset_category = self.get_asset_category()
			finance_books = get_finance_books(asset_category)
			self.set('finance_books', finance_books)

		elif self.doctype == "Asset_" and not self.get('asset_category'):
			self.set_asset_category()

	def set_initial_asset_value(self):
		self.asset_value = self.get_initial_asset_value()

	def get_initial_asset_value(self):
		purchase_doc = get_purchase_details(self)
		gross_purchase_amount, opening_accumulated_depreciation = self.get_gross_purchase_amount_and_opening_accumulated_depreciation()

		if self.is_depreciable_asset() and not purchase_doc:
			asset_value = gross_purchase_amount - opening_accumulated_depreciation
		else:
			asset_value = gross_purchase_amount

		return asset_value

	def get_asset_category(self):
		if self.doctype == "Asset_":
			if not self.get('asset_category'):
				self.set_asset_category()

			return self.asset_category
		else:
			return self.asset_values["asset_category"]

	def set_asset_category(self):
		if not self.get('asset_category'):
			self.asset_category = frappe.get_cached_value("Item", self.item_code, "asset_category")

	def get_gross_purchase_amount_and_opening_accumulated_depreciation(self):
		if self.doctype == "Asset_":
			return self.gross_purchase_amount, self.opening_accumulated_depreciation
		else:
			return self.asset_values["gross_purchase_amount"], self.asset_values["opening_accumulated_depreciation"]

	def validate_available_for_use_date(self):
		purchase_date = self.get_purchase_date()

		if self.available_for_use_date and getdate(self.available_for_use_date) < getdate(purchase_date):
			frappe.throw(_("Available-for-use Date should be after purchase date"))

	def create_schedules_if_depr_details_have_been_updated(self):
		if self.has_value_changed("available_for_use_date") or self.has_value_changed("gross_purchase_amount"):
			delete_existing_schedules(self)
			create_depreciation_schedules(self)

			if self.has_value_changed("gross_purchase_amount"):
				self.set_initial_asset_value()

			self.set_initial_asset_value_for_finance_books()
			return

		doc_before_save = self.get_doc_before_save()

		if self.has_updated_finance_books(doc_before_save):
			old_finance_books = doc_before_save.get("finance_books")

			self.delete_schedules_belonging_to_deleted_finance_books(old_finance_books)
			self.create_new_schedules_for_new_finance_books(old_finance_books)

			self.set_initial_asset_value_for_finance_books()

	def set_initial_asset_value_for_finance_books(self):
		for row in self.finance_books:
			row.asset_value = self.asset_value

	def update_asset_value(self, change_in_value=0):
		if self.get('finance_books'):
			self.asset_value = self.finance_books[0].asset_value
		else:
			self.asset_value += change_in_value

	def has_updated_finance_books(self, doc_before_save):
		return doc_before_save.get("finance_books") != self.get("finance_books")

	def create_new_schedules_for_new_finance_books(self, old_finance_books):
		for fb in self.finance_books:
			if fb not in old_finance_books:
				delete_existing_schedules(self, fb)
				create_schedule_for_finance_book(self, fb)
			else:
				old_finance_books.remove(fb)

	def delete_schedules_belonging_to_deleted_finance_books(self, old_finance_books):
		for fb in old_finance_books:
			delete_existing_schedules(self, fb)

	def get_purchase_date(self):
		if self.doctype == "Asset_":
			return self.purchase_date
		else:
			return self.asset_values["purchase_date"]

	def validate_depreciation_posting_start_date(self):
		for finance_book in self.finance_books:
			if finance_book.depreciation_posting_start_date == self.available_for_use_date:
				frappe.throw(_("Row #{}: Depreciation Posting Date should not be equal to Available for Use Date.")
					.format(finance_book.idx), title=_("Incorrect Date"))

	def submit_depreciation_schedules(self, notes=None):
		filters = {
			"asset": self.get_asset(),
			"serial_no": self.get_serial_no()
		}

		depreciation_schedules = frappe.get_all(
			"Depreciation Schedule_",
			filters = filters,
			fields = ["name", "status"]
		)

		for schedule in depreciation_schedules:
			if schedule["status"] == "Draft":
				ds = frappe.get_doc("Depreciation Schedule_", schedule["name"])
				ds.submit()
			elif schedule["status"] == "Active":
				self.cancel_active_schedule(schedule["name"], notes)

	def cancel_active_schedule(self, schedule_name, notes):
		active_schedule = frappe.get_doc("Depreciation Schedule_", schedule_name)

		active_schedule.flags.ignore_validate_update_after_submit = True
		active_schedule.notes = notes
		active_schedule.status = "Cancelled"
		active_schedule.save()

		active_schedule.cancel()

	def record_asset_purchase(self):
		purchase_doctype, purchase_docname = get_purchase_details(self)

		if purchase_docname:
			serial_no = self.get_serial_no()
			asset = self.get_asset()

			create_asset_activity(
				asset = asset,
				asset_serial_no = serial_no,
				activity_type = 'Purchase',
				reference_doctype = purchase_doctype,
				reference_docname = purchase_docname,
				activity_date = self.get_purchase_date()
			)

	def record_asset_creation(self):
		asset = self.get_asset()
		serial_no = self.get_serial_no()

		create_asset_activity(
			asset = asset,
			asset_serial_no = serial_no,
			activity_type = 'Creation',
			reference_doctype = self.doctype,
			reference_docname = self.name
		)

	def record_asset_receipt(self):
		reference_doctype, reference_docname = get_purchase_details(self)
		transaction_date = getdate(self.get_purchase_date())
		serial_no = self.get_serial_no()
		asset = self.get_asset()
		asset_name, company = self.get_asset_details()

		if reference_docname:
			posting_date, posting_time = frappe.db.get_value(
				reference_doctype, reference_docname, ["posting_date", "posting_time"]
			)
			transaction_date = get_datetime("{} {}".format(posting_date, posting_time))

		assets = [{
			'asset': asset,
			'asset_name': asset_name,
			'serial_no': serial_no,
			'target_location': self.location,
			'to_employee': self.custodian
		}]

		asset_movement = frappe.get_doc({
			'doctype': 'Asset Movement_',
			'assets': assets,
			'purpose': 'Receipt',
			'company': company,
			'transaction_date': transaction_date,
			'reference_doctype': reference_doctype,
			'reference_name': reference_docname
		}).insert()
		asset_movement.submit()

	def get_serial_no(self):
		if self.doctype == "Asset_":
			return ""
		else:
			return self.serial_no

	def get_asset(self):
		if self.doctype == "Asset_":
			return self.name
		else:
			return self.asset

	def get_asset_details(self):
		if self.doctype == "Asset_":
			return self.asset_name, self.company
		else:
			return self.asset_values["asset_name"], self.asset_values["company"]

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

			elif self.is_depreciable_asset() and self.finance_books:
				idx = self.get_default_finance_book_idx() or 0

				salvage_value = self.finance_books[idx].salvage_value
				asset_value = self.finance_books[idx].asset_value

				if flt(asset_value) <= salvage_value:
					status = "Fully Depreciated"
				elif flt(asset_value) < flt(self.gross_purchase_amount):
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
	if isinstance(assets, str):
		assets = json.loads(assets)

	if len(assets) == 0:
		frappe.throw(_('Atleast one asset has to be selected.'))

	asset_movement = frappe.new_doc("Asset Movement_")
	asset_movement.quantity = len(assets)
	asset_movement.purpose = purpose

	for asset in assets:
		location, custodian, company, asset_name, serial_no  = fetch_asset_tracking_details(asset)

		asset_movement.company = company
		asset_movement.append("assets", {
			'asset': asset_name,
			'source_location': location,
			'from_employee': custodian,
			'serial_no': serial_no
		})

	if asset_movement.get('assets'):
		return asset_movement.as_dict()

def fetch_asset_tracking_details(asset):
	asset = frappe._dict(asset)

	if asset.get("serial_no"):
		location, custodian = frappe.get_value("Asset Serial No", asset.name, ["location", "custodian"])
		company = frappe.get_value("Asset_", asset.asset, "company")
		asset_name = asset.asset
		serial_no = asset.name
	else:
		location, custodian, company = frappe.get_value("Asset_", asset.name, ["location", "custodian", "company"])
		asset_name = asset.name
		serial_no = ""

	return location, custodian, company, asset_name, serial_no

@frappe.whitelist()
def get_purchase_details(asset):
	if isinstance(asset, str):
		asset = frappe._dict(json.loads(asset))

	if asset.doctype == "Asset_":
		purchase_receipt, purchase_invoice = asset.purchase_receipt, asset.purchase_invoice
	else:
		purchase_receipt, purchase_invoice = frappe.db.get_value(
			"Asset_",
			asset.asset,
			["purchase_receipt", "purchase_invoice"]
		)

	purchase_doctype = 'Purchase Receipt' if purchase_receipt else 'Purchase Invoice'
	purchase_docname = purchase_receipt or purchase_invoice

	return purchase_doctype, purchase_docname

@frappe.whitelist()
def get_num_of_items_in_purchase_doc(asset, purchase_doctype, purchase_docname):
	if isinstance(asset, str):
		asset = frappe._dict(json.loads(asset))

	items_doctype = purchase_doctype + " Item"
	item = get_item(asset)

	num_of_items_in_purchase_doc = frappe.db.get_value(
		items_doctype,
		{
			"parent": purchase_docname,
			"item_code": item
		},
		"qty"
	)
	return num_of_items_in_purchase_doc

def get_item(asset):
	if asset.doctype == "Asset_":
		return asset.item_code
	else:
		return frappe.db.get_value("Asset_", asset.asset, "item_code")

def validate_serial_no(doc):
	is_serialized_asset = frappe.db.get_value('Asset_', doc.asset, 'is_serialized_asset')

	if is_serialized_asset and not doc.serial_no:
		frappe.throw(_("Please enter Serial No as {0} is a Serialized Asset")
			.format(frappe.bold(doc.asset)), title=_("Missing Serial No"))

@frappe.whitelist()
def transfer_asset(asset, purpose, source_location, company):
	movement_entry = frappe.new_doc("Asset Movement_")
	movement_entry.company = company
	movement_entry.purpose = purpose
	movement_entry.transaction_date = get_datetime()

	movement_entry.append("assets", {
		"asset": asset,
		"source_location": source_location
	})

	return movement_entry

@frappe.whitelist()
def make_sales_invoice(asset, item_code, company):
	si = frappe.new_doc("Sales Invoice")
	si.company = company
	si.currency = frappe.get_cached_value('Company',  company,  "default_currency")
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)

	si.append("items", {
		"item_code": item_code,
		"is_fixed_asset": 1,
		"asset": asset,
		"income_account": disposal_account,
		"cost_center": depreciation_cost_center,
		"qty": 1
	})
	si.set_missing_values()

	return si

def get_disposal_account_and_cost_center(company):
	disposal_account, depreciation_cost_center = frappe.get_cached_value('Company',  company,
		["disposal_account", "depreciation_cost_center"])

	if not disposal_account:
		frappe.throw(_("Please set 'Gain/Loss Account on Asset Disposal' in Company {0}").format(company))
	if not depreciation_cost_center:
		frappe.throw(_("Please set 'Asset Depreciation Cost Center' in Company {0}").format(company))

	return disposal_account, depreciation_cost_center

@frappe.whitelist()
def create_asset_maintenance(asset, item_code, item_name, asset_category, company):
	asset_maintenance = frappe.new_doc("Asset Maintenance_")
	asset_maintenance.update({
		"asset_name": asset,
		"company": company,
		"item_code": item_code,
		"item_name": item_name,
		"asset_category": asset_category
	})

	return asset_maintenance

@frappe.whitelist()
def create_asset_repair(asset, asset_name):
	asset_repair = frappe.new_doc("Asset Repair_")
	asset_repair.update({
		"asset": asset,
		"asset_name": asset_name
	})

	return asset_repair

@frappe.whitelist()
def make_journal_entry(asset_name):
	asset = frappe.get_doc("Asset_", asset_name)
	_, accumulated_depreciation_account, depreciation_expense_account = \
		get_depreciation_accounts(asset)

	depreciation_cost_center, depreciation_series = frappe.db.get_value("Company", asset.company,
		["depreciation_cost_center", "series_for_depreciation_entry"])
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depreciation_series
	je.company = asset.company
	je.remark = "Depreciation Entry against asset {0}".format(asset_name)

	je.append("accounts", {
		"account": depreciation_expense_account,
		"reference_type": "Asset",
		"reference_name": asset.name,
		"cost_center": depreciation_cost_center
	})

	je.append("accounts", {
		"account": accumulated_depreciation_account,
		"reference_type": "Asset",
		"reference_name": asset.name
	})

	return je

def get_depreciation_accounts(asset):
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None

	accounts = frappe.db.get_value("Asset Category Account_",
		filters={'parent': asset.asset_category, 'company_name': asset.company},
		fieldname = ['fixed_asset_account', 'accumulated_depreciation_account',
			'depreciation_expense_account'], as_dict=1)

	if accounts:
		fixed_asset_account = accounts.fixed_asset_account
		accumulated_depreciation_account = accounts.accumulated_depreciation_account
		depreciation_expense_account = accounts.depreciation_expense_account

	if not accumulated_depreciation_account or not depreciation_expense_account:
		accounts = frappe.get_cached_value('Company',  asset.company,
			["accumulated_depreciation_account", "depreciation_expense_account"])

		if not accumulated_depreciation_account:
			accumulated_depreciation_account = accounts[0]
		if not depreciation_expense_account:
			depreciation_expense_account = accounts[1]

	if not fixed_asset_account or not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}")
			.format(asset.asset_category, asset.company))

	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account