# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, date_diff

from assets.controllers.base_asset import validate_serial_no

class DepreciationSchedule_(Document):
	def validate(self):
		validate_serial_no(self)
		self.prepare_depreciation_data()

	def prepare_depreciation_data(self, date_of_sale=None):
		self.make_depreciation_schedule(date_of_sale)

	def make_depreciation_schedule(self, date_of_sale):
		asset = frappe.get_doc("Asset_", self.asset)
		initial_asset_value = asset.get_initial_asset_value()

		finance_books, available_for_use_date = self.get_depr_details(asset)

		for row in finance_books:
			depreciable_value = initial_asset_value - row.salvage_value
			depr_template = frappe.get_doc("Depreciation Template", row.depreciation_template)

			if depr_template.depreciation_method == "Straight Line":
				frequency_of_depr = self.get_frequency_of_depreciation_in_months(depr_template.frequency_of_depreciation)
				depr_period = self.get_depreciation_period_in_months(depr_template)

				depr_end_date = self.get_depreciation_end_date(available_for_use_date, depr_period, date_of_sale)

				depr_start_date = available_for_use_date
				schedule_date = row.depreciation_posting_start_date

				depr_in_one_day = self.get_depreciation_in_one_day(available_for_use_date, depr_period, depr_start_date, depreciable_value)

				while schedule_date < depr_end_date:
					self.create_depreciation_entry(schedule_date, depr_start_date, depr_in_one_day, row.finance_book)

					depr_start_date = schedule_date
					schedule_date = add_months(schedule_date, frequency_of_depr)

				# for the final row
				self.create_depreciation_entry(depr_end_date, depr_start_date, depr_in_one_day, row.finance_book)

	def get_depr_details(self, asset):
		if self.serial_no:
			doc = frappe.get_doc("Asset Serial No", self.serial_no)
		else:
			doc = asset

		return doc.finance_books, doc.available_for_use_date

	def get_frequency_of_depreciation_in_months(self, frequency_of_depreciation):
		frequency_in_months = {
			"Monthly": 1,
			"Every 2 months": 2,
			"Quarterly": 3,
			"Every 4 months": 4,
			"Every 5 months": 5,
			"Half-Yearly": 6,
			"Every 7 months": 7,
			"Every 8 months": 8,
			"Every 9 months": 9,
			"Every 10 months": 10,
			"Every 11 months": 11,
			"Yearly": 12
		}

		return frequency_in_months[frequency_of_depreciation]

	def get_depreciation_period_in_months(self, depreciation_template):
		if depreciation_template.depreciation_period_unit == "Months":
			return depreciation_template.depreciation_period
		else:
			return (depreciation_template.depreciation_period * 12)

	def get_depreciation_end_date(self, available_for_use_date, depr_period, date_of_sale):
		if date_of_sale:
			return date_of_sale

		return add_months(available_for_use_date, depr_period)

	def get_depreciation_in_one_day(self, available_for_use_date, depr_period, depr_start_date, depreciable_value):
		depr_end_date = add_months(available_for_use_date, depr_period)
		depr_period_in_days = date_diff(depr_end_date, depr_start_date) + 1

		return depreciable_value / depr_period_in_days

	def create_depreciation_entry(self, schedule_date, depr_start_date, depr_in_one_day, finance_book):
		days_of_depr = date_diff(schedule_date, depr_start_date) + 1
		depr_amount = depr_in_one_day * days_of_depr

		if depr_amount > 0:
			self.append("depreciation_schedule", {
				"finance_book": finance_book,
				"schedule_date": schedule_date,
				"depreciation_amount": depr_amount
			})