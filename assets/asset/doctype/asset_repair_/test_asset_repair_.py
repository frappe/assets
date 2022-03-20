# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import nowdate, flt

from assets.asset.doctype.asset_.test_asset_ import (
	create_asset,
	create_company,
	create_asset_data,
)
from assets.asset.doctype.asset_serial_no.test_asset_serial_no import get_asset_serial_no_doc

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

	def test_asset_status_gets_updated_on_repair(self):
		asset = create_asset(submit = 1)
		initial_status = asset.status
		asset_repair = create_asset_repair(asset = asset)

		if asset_repair.repair_status == "Pending":
			asset.reload()
			self.assertEqual(asset.status, "Out of Order")

		asset_repair.repair_status = "Completed"
		asset_repair.save()

		asset.reload()
		final_status = asset.status

		self.assertEqual(final_status, initial_status)

	def test_asset_serial_no_status_gets_updated_on_repair(self):
		asset = create_asset(is_serialized_asset = 1, submit = 1)
		asset_serial_no = get_asset_serial_no_doc(asset.name)

		initial_status = asset_serial_no.status
		asset_repair = create_asset_repair(asset = asset, asset_serial_no = asset_serial_no.name)

		if asset_repair.repair_status == "Pending":
			asset_serial_no.reload()
			self.assertEqual(asset_serial_no.status, "Out of Order")

		asset_repair.repair_status = "Completed"
		asset_repair.save()

		asset_serial_no.reload()
		final_status = asset_serial_no.status

		self.assertEqual(final_status, initial_status)

	def test_amount_calculation_for_stock_items(self):
		asset_repair = create_asset_repair(stock_consumption = 1)

		for item in asset_repair.items:
			amount = flt(item.rate) * flt(item.qty)
			self.assertEqual(item.amount, amount)

	def test_total_repair_cost_calculation(self):
		asset_repair = create_asset_repair(stock_consumption = 1)
		total_repair_cost = asset_repair.repair_cost

		for item in asset_repair.items:
			total_repair_cost += item.amount

		self.assertEqual(total_repair_cost, asset_repair.total_repair_cost)

def create_asset_repair(**args):
	from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	args = frappe._dict(args)

	if args.asset:
		asset = args.asset
	else:
		asset = create_asset(submit=1)

	asset_repair = frappe.new_doc("Asset Repair_")
	asset_repair.update({
		"asset": asset.name,
		"asset_name": asset.asset_name,
		"serial_no": args.asset_serial_no,
		"num_of_assets": args.num_of_assets or (0 if args.asset_serial_no else 1),
		"failure_date": args.failure_date or nowdate(),
		"description": "Test Description",
		"repair_cost": args.repair_cost,
		"company": asset.company
	})

	if args.stock_consumption:
		asset_repair.stock_consumption = 1
		asset_repair.warehouse = args.warehouse or create_warehouse("Test Warehouse", company = asset.company)
		asset_repair.append("items", {
			"item_code": args.item_code or "_Test Stock Item",
			"rate": args.rate if args.get("rate") is not None else 100,
			"qty": args.qty or 1,
			"serial_no": args.stock_item_serial_no
		})

	asset_repair.insert(ignore_if_duplicate=True)

	if args.submit:
		asset_repair.repair_status = "Completed"
		asset_repair.cost_center = "_Test Cost Center - _TC"

		if args.stock_consumption:
			stock_entry = frappe.get_doc({
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": asset.company
			})
			stock_entry.append('items', {
				"t_warehouse": asset_repair.warehouse,
				"item_code": asset_repair.stock_items[0].item_code,
				"qty": asset_repair.stock_items[0].consumed_quantity
			})
			stock_entry.submit()

		if args.capitalize_repair_cost:
			asset_repair.capitalize_repair_cost = 1
			asset_repair.repair_cost = 1000

			if asset.calculate_depreciation:
				asset_repair.increase_in_asset_life = 12

			asset_repair.purchase_invoice = make_purchase_invoice().name

		asset_repair.submit()

	return asset_repair
