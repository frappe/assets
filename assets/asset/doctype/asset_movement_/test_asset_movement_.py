# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import frappe
import unittest

from assets.asset.doctype.asset_.test_asset_ import (
	create_asset,
	create_company,
	create_asset_data,
)

class TestAssetMovement_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_movement_is_created_on_asset_submission(self):
		asset = create_asset(submit=1)
		asset_movement = frappe.get_last_doc("Asset Movement_")

		self.assertEqual(asset_movement.purpose, "Receipt")
		self.assertEqual(asset_movement.assets[0].asset, asset.name)
