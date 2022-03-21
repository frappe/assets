# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import frappe
import unittest

from frappe.utils import nowdate

from assets.asset.doctype.asset_.test_asset_ import (
	create_asset,
	create_company,
	create_location,
	create_asset_data,
)

class TestAssetMovement_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		create_location("Test Location2")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_movement_is_created_on_asset_submission(self):
		asset = create_asset(submit=1)
		asset_movement = frappe.get_last_doc("Asset Movement_")

		self.assertEqual(asset_movement.purpose, "Receipt")
		self.assertEqual(asset_movement.assets[0].asset, asset.name)

	def test_transfer_draft_asset(self):
		asset = create_asset(submit = 0)
		asset_movement = create_asset_movement(
			purpose = "Transfer",
			company = asset.company,
			assets = [{
				"asset": asset.name ,
				"source_location": "Test Location",
				"target_location": "Test Location2"
			}],
			do_not_save = 1
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_employee_or_location_are_mandatory(self):
		asset = create_asset(submit = 1)
		asset_movement = create_asset_movement(
			purpose = "Transfer",
			company = asset.company,
			assets = [{
				"asset": asset.name
			}],
			do_not_save = 1
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_serial_no_mandatory_for_serialized_asset(self):
		asset = create_asset(is_serialized_asset = 1, submit = 1)
		asset_movement = create_asset_movement(
			purpose = "Transfer",
			company = asset.company,
			assets = [{
				"asset": asset.name,
				"source_location": "Test Location",
				"target_location": "Test Location2"
			}],
			do_not_save = 1
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

def create_asset_movement(**args):
	args = frappe._dict(args)

	if not args.transaction_date:
		args.transaction_date = nowdate()

	movement = frappe.new_doc("Asset Movement_")
	movement.update({
		"assets": args.assets,
		"transaction_date": args.transaction_date,
		"company": args.company or "_Test Company",
		"purpose": args.purpose or "Receipt",
		"reference_doctype": args.reference_doctype,
		"reference_name": args.reference_name
	})

	if not args.do_not_save:
		movement.insert()

		if args.submit:
			movement.submit()

	return movement