# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, time_diff_in_hours, get_link_to_form
from erpnext.controllers.accounts_controller import AccountsController

from assets.controllers.base_asset import get_asset_account
from assets.asset.doctype.asset_.asset_ import split_asset
from erpnext.accounts.general_ledger import make_gl_entries


class AssetRepair_(AccountsController):
	def validate(self):
		self.get_asset_doc()
		self.validate_asset()
		self.update_status()

		if self.get('stock_consumption'):
			self.set_total_value()

		self.calculate_total_repair_cost()

	def before_submit(self):
		self.check_repair_status()
		self.split_asset_doc_if_required()

		if self.get('stock_consumption') or self.get('capitalize_repair_cost'):
			self.increase_asset_value()
		if self.get('stock_consumption'):
			self.decrease_stock_quantity()
		if self.get('capitalize_repair_cost'):
			self.make_gl_entries()

			if self.is_depreciable_asset() and self.get('increase_in_asset_life'):
				self.increase_asset_life()

	def before_cancel(self):
		self.get_asset_doc()

		if self.get('stock_consumption') or self.get('capitalize_repair_cost'):
			self.decrease_asset_value()
		if self.get('stock_consumption'):
			self.increase_stock_quantity()
		if self.get('capitalize_repair_cost'):
			self.ignore_linked_doctypes = ('GL Entry', 'Stock Ledger Entry')
			self.make_gl_entries(cancel=True)

			if self.is_depreciable_asset() and self.get('increase_in_asset_life'):
				self.decrease_asset_life()

	def get_asset_doc(self):
		if self.get('serial_no'):
			self.asset_doc = frappe.get_doc('Asset Serial No', self.serial_no)
		else:
			self.asset_doc = frappe.get_doc('Asset_', self.asset)

	def validate_asset(self):
		if self.asset_doc.doctype == 'Asset_':
			if self.asset_doc.is_serialized_asset:
				self.validate_serial_no()
			else:
				self.validate_num_of_assets()

	def validate_serial_no(self):
		if not self.serial_no:
			frappe.throw(_("Please enter Serial No as {0} is a Serialized Asset")
				.format(frappe.bold(self.asset)), title=_("Missing Serial No"))

	def validate_num_of_assets(self):
		if self.num_of_assets > self.asset_doc.num_of_assets:
			frappe.throw(_("Number of Assets cannot be greater than {0}")
				.format(frappe.bold(self.asset_doc.num_of_assets)), title=_("Number Exceeded Limit"))

		if self.num_of_assets < 1:
			frappe.throw(_("Number of Assets needs to be between <b>1</b> and {0}")
				.format(frappe.bold(self.asset_doc.num_of_assets)), title=_("Invalid Number"))

	def update_status(self):
		if self.repair_status == 'Pending':
			frappe.db.set_value(self.asset_doc.doctype, self.asset_doc.name, 'status', 'Out of Order')
		else:
			self.asset_doc.set_status()

	def set_total_value(self):
		for item in self.get('items'):
			item.amount = flt(item.rate) * flt(item.qty)

	def calculate_total_repair_cost(self):
		self.total_repair_cost = flt(self.repair_cost)

		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		self.total_repair_cost += total_value_of_stock_consumed

	def get_total_value_of_stock_consumed(self):
		total_value_of_stock_consumed = 0
		if self.get('stock_consumption'):
			for item in self.get('items'):
				total_value_of_stock_consumed += item.amount

		return total_value_of_stock_consumed

	def check_repair_status(self):
		if self.repair_status == "Pending":
			frappe.throw(_("Please update Repair Status."))

	def split_asset_doc_if_required(self):
		if self.asset_doc.doctype == "Asset_" and not self.asset_doc.is_serialized_asset:
			if self.num_of_assets < self.asset_doc.num_of_assets:
				num_of_assets_to_be_separated = self.asset_doc.num_of_assets - self.num_of_assets

				split_asset(self.asset_doc, num_of_assets_to_be_separated)

	def increase_asset_value(self):
		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		increase_in_value = self.get_change_in_value(total_value_of_stock_consumed)

		if self.is_depreciable_asset():
			for row in self.asset_doc.finance_books:
				row.asset_value += increase_in_value

			self.asset_doc.update_asset_value()
		else:
			self.asset_doc.update_asset_value(increase_in_value)

		self.asset_doc.flags.ignore_validate_update_after_submit = True
		self.asset_doc.save()

	def decrease_asset_value(self):
		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		decrease_in_value = self.get_change_in_value(total_value_of_stock_consumed)

		if self.is_depreciable_asset():
			for row in self.asset_doc.finance_books:
				row.asset_value -= decrease_in_value

			self.asset_doc.update_asset_value()
		else:
			self.asset_doc.update_asset_value(-decrease_in_value)

		self.asset_doc.flags.ignore_validate_update_after_submit = True
		self.asset_doc.save()

	def get_change_in_value(self, total_value_of_stock_consumed):
		change_in_value = total_value_of_stock_consumed
		if self.capitalize_repair_cost:
			change_in_value += self.repair_cost

		return change_in_value

	def is_depreciable_asset(self):
		if self.asset_doc.doctype == "Asset_":
			return self.asset_doc.calculate_depreciation
		else:
			return frappe.db.get_value("Asset_", self.asset_doc.asset, "calculate_depreciation")

	def decrease_stock_quantity(self):
		stock_entry = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": self.company
		})

		for item in self.get('items'):
			stock_entry.append('items', {
				"s_warehouse": self.warehouse,
				"item_code": item.item_code,
				"qty": item.qty,
				"basic_rate": item.rate,
				"serial_no": item.serial_no
			})

		stock_entry.insert()
		stock_entry.submit()

		self.db_set('stock_entry', stock_entry.name)

	def increase_stock_quantity(self):
		stock_entry = frappe.get_doc('Stock Entry', self.stock_entry)
		stock_entry.flags.ignore_links = True
		stock_entry.cancel()

	def make_gl_entries(self, cancel=False):
		if flt(self.repair_cost) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entries = []
		repair_and_maintenance_account = frappe.db.get_value('Company', self.company, 'repair_and_maintenance_account')
		fixed_asset_account = get_asset_account("fixed_asset_account", asset=self.asset, company=self.company)
		expense_account = frappe.get_doc('Purchase Invoice', self.purchase_invoice).items[0].expense_account

		gl_entries.append(
			self.get_gl_dict({
				"account": expense_account,
				"credit": self.repair_cost,
				"credit_in_account_currency": self.repair_cost,
				"against": repair_and_maintenance_account,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"cost_center": self.cost_center,
				"posting_date": getdate(),
				"company": self.company
			}, item=self)
		)

		if self.get('stock_consumption'):
			# creating GL Entries for each row in Stock Items based on the Stock Entry created for it
			stock_entry = frappe.get_doc('Stock Entry', self.stock_entry)
			for item in stock_entry.items:
				gl_entries.append(
					self.get_gl_dict({
						"account": item.expense_account,
						"credit": item.amount,
						"credit_in_account_currency": item.amount,
						"against": repair_and_maintenance_account,
						"voucher_type": self.doctype,
						"voucher_no": self.name,
						"cost_center": self.cost_center,
						"posting_date": getdate(),
						"company": self.company
					}, item=self)
				)

		gl_entries.append(
			self.get_gl_dict({
				"account": fixed_asset_account,
				"debit": self.total_repair_cost,
				"debit_in_account_currency": self.total_repair_cost,
				"against": expense_account,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"cost_center": self.cost_center,
				"posting_date": getdate(),
				"against_voucher_type": "Purchase Invoice",
				"against_voucher": self.purchase_invoice,
				"company": self.company
			}, item=self)
		)

		return gl_entries

	def increase_asset_life(self):
		self.asset_doc.flags.ignore_validate_update_after_submit = True

		for row in self.asset_doc.finance_books:
			self.replace_depreciation_template(row)

		self.asset_doc.create_schedules_if_depr_details_have_been_updated()
		self.asset_doc.submit_depreciation_schedules(notes =
			_("This schedule was cancelled because {0} underwent a repair({1}) that extended its life.")
			.format(
				get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
				get_link_to_form(self.doctype, self.name)
			)
		)
		self.asset_doc.save()

	def replace_depreciation_template(self, row):
		new_depr_template = self.create_copy_of_depreciation_template(row.depreciation_template)
		self.update_asset_life_in_new_template(new_depr_template)
		new_depr_template.submit()

		row.depreciation_template = new_depr_template.name

	def create_copy_of_depreciation_template(self, current_template_name):
		current_template_details = frappe.get_value(
			"Depreciation Template",
			current_template_name,
			["template_name", "depreciation_method", "frequency_of_depreciation", "asset_life", "asset_life_unit", "rate_of_depreciation"],
			as_dict = 1
		)

		new_depr_template = frappe.new_doc("Depreciation Template")
		new_depr_template.template_name = current_template_details["template_name"] + " - Modified Copy"
		new_depr_template.depreciation_method = current_template_details["depreciation_method"]
		new_depr_template.frequency_of_depreciation = current_template_details["frequency_of_depreciation"]
		new_depr_template.asset_life = current_template_details["asset_life"]
		new_depr_template.asset_life_unit = current_template_details["asset_life_unit"]
		new_depr_template.rate_of_depreciation = current_template_details["rate_of_depreciation"]

		return new_depr_template

	def update_asset_life_in_new_template(self, new_depr_template):
		if new_depr_template.asset_life_unit == "Months":
			new_depr_template.asset_life += self.increase_in_asset_life
		else:
			# asset_life should be an integer
			if self.increase_in_asset_life % 12 == 0:
				new_depr_template.asset_life += self.increase_in_asset_life / 12
			else:
				new_depr_template.asset_life_unit = "Months"
				new_depr_template.asset_life += self.increase_in_asset_life

	def decrease_asset_life(self):
		self.asset_doc.flags.ignore_validate_update_after_submit = True

		for row in self.asset_doc.finance_books:
			self.replace_with_original_depreciation_template(row)

		self.asset_doc.create_schedules_if_depr_details_have_been_updated()
		self.asset_doc.submit_depreciation_schedules(notes =
			_("This schedule was cancelled because the repair that extended {0}'s life({1}) was cancelled.")
			.format(
				get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
				get_link_to_form(self.doctype, self.name)
			)
		)
		self.asset_doc.save()

	def replace_with_original_depreciation_template(self, row):
		old_depr_template = self.get_old_depreciation_template(row.depreciation_template)
		row.depreciation_template = old_depr_template

	def get_old_depreciation_template(self, current_template_name):
		if isinstance(current_template_name, str):
			# because " - Modified Copy" was added at the end of the original template to create the new one's name
			if current_template_name[-16:] == " - Modified Copy":
				old_template_length = len(current_template_name) - 16
				old_template_name = current_template_name[:old_template_length]

				return old_template_name

		frappe.throw(_("Cannot find original Depreciation Template."))

@frappe.whitelist()
def get_downtime(failure_date, completion_date):
	downtime = time_diff_in_hours(completion_date, failure_date)
	return round(downtime, 2)