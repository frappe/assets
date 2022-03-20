# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import frappe
import unittest

from assets.asset.doctype.asset_.test_asset_ import (
	create_asset,
	create_company,
	create_asset_data,
)
from erpnext.stock.doctype.item.test_item import create_item

class TestAssetRepair_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		create_item("_Test Stock Item")
		frappe.db.sql("delete from `tabTax Rule`")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
