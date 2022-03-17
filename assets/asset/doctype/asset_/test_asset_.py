# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import frappe
import unittest

from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

class TestAsset_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		enable_cwip_accounting("Computers")
		enable_book_asset_depreciation_entry_automatically()
		make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location")
		frappe.db.sql("delete from `tabTax Rule`")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

def create_company():
	if not frappe.db.exists("Company", "_Test Company"):
		company = frappe.get_doc({
			"doctype": "Company",
			"company_name": "_Test Company",
			"country": "United States",
			"default_currency": "USD",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC",
			"disposal_account": "_Test Gain/Loss on Asset Disposal - _TC",
			"depreciation_cost_center": "_Test Cost Center - _TC",
		})
		company.insert(ignore_if_duplicate = True)
	else:
		set_depreciation_settings_in_company()

def set_depreciation_settings_in_company():
	company = frappe.get_doc("Company", "_Test Company")
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - _TC"
	company.depreciation_expense_account = "_Test Depreciations - _TC"
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - _TC"
	company.depreciation_cost_center = "_Test Cost Center - _TC"
	company.save()

def create_asset_data():
	if not frappe.db.exists("Asset Category_", "Computers"):
		create_asset_category()

	if not frappe.db.exists("Item", "Macbook Pro"):
		create_fixed_asset_item()

	if not frappe.db.exists("Location_", "Test Location"):
		create_location()

def create_asset_category():
	asset_category = frappe.get_doc({
		"doctype": "Asset Category_",
		"asset_category_name": "Computers",
		"enable_cwip_accounting": 1,
		"accounts": [{
			"company_name": "_Test Company",
			"fixed_asset_account": "_Test Fixed Asset - _TC",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC"
		}]
	})

	asset_category.insert()

def create_fixed_asset_item(item_code=None):
	naming_series = get_naming_series()

	try:
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code or "Macbook Pro",
			"item_name": "Macbook Pro",
			"description": "Macbook Pro Retina Display",
			"asset_category": "Computers",
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_fixed_asset": 1,
			"auto_create_assets": 1,
			"asset_naming_series": naming_series
		})
		item.insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	return item

def get_naming_series():
	meta = frappe.get_meta("Asset_")
	naming_series = meta.get_field("naming_series").options.splitlines()[0] or "ACC-ASS-.YYYY.-"

	return naming_series

def create_location():
	frappe.get_doc({
		"doctype": "Location_",
		"location_name": "Test Location"
	}).insert()

def enable_cwip_accounting(asset_category, enable=1):
	frappe.db.set_value("Asset Category_", asset_category, "enable_cwip_accounting", enable)

def enable_book_asset_depreciation_entry_automatically():
	frappe.db.set_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically", 1)
