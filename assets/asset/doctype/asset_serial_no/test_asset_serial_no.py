# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import getdate

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

	def test_num_of_asset_serial_nos_created(self):
		"""Tests if x Asset Serial Nos are created when num_of_assets = x in the Asset doc."""

		asset = create_asset(is_serialized_asset=1, num_of_assets=5, submit=1)
		asset_serial_nos = get_linked_asset_serial_nos(asset.name)

		self.assertEqual(len(asset_serial_nos), 5)

	def test_available_for_use_date_is_after_purchase_date(self):
		asset = create_asset(is_serialized_asset=1, calculate_depreciation=1, submit=1)

		asset_serial_no = get_linked_asset_serial_nos(asset.name)[0]
		asset_serial_no_doc = frappe.get_doc("Asset Serial No", asset_serial_no.name)

		asset.purchase_date = getdate("2021-10-10")
		asset_serial_no_doc.available_for_use_date = getdate("2021-10-1")

		self.assertRaises(frappe.ValidationError, asset_serial_no_doc.save)

def get_linked_asset_serial_nos(asset_name, fields=["name"]):
	return frappe.get_all(
		"Asset Serial No",
		filters = {
			"asset": asset_name
		},
		fields = fields
	)
