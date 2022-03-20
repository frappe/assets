# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import frappe
import unittest

from assets.asset.doctype.asset_.test_asset_ import (
	create_asset,
	create_company,
	create_asset_data,
	enable_cwip_accounting,
	enable_book_asset_depreciation_entry_automatically,
)
class TestAssetSerialNo(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		enable_cwip_accounting("Computers")
		enable_book_asset_depreciation_entry_automatically()
		# make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location")
		frappe.db.sql("delete from `tabTax Rule`")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
