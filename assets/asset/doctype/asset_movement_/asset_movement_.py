# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class AssetMovement_(Document):
	def validate(self):
		self.validate_asset()
		self.validate_movement()
		self.validate_employee()

	def validate_asset(self):
		for asset in self.assets:
			status, company = frappe.db.get_value("Asset", asset.asset, ["status", "company"])

			if self.purpose == 'Transfer' and status in ("Draft", "Scrapped", "Sold"):
				frappe.throw(_("Row {0}: {1} asset cannot be transferred.").format(asset.idx, status))

			if company != self.company:
				frappe.throw(_("{0} does not belong to company {1}.").format(asset.asset, self.company))

			if not (asset.source_location or asset.target_location or asset.from_employee or asset.to_employee):
				frappe.throw(_("Either location or employee must be entered."))

	def validate_movement(self):
		for asset in self.assets:
			if self.purpose in ['Transfer', 'Issue']:
				self.validate_source_location(asset)

				if self.purpose == 'Issue':
					self.validate_asset_issue(asset)
				if self.purpose == 'Transfer':
					self.validate_asset_transfer(asset)

			else:
				self.validate_asset_receipt(asset)

	def validate_source_location(self, asset):
		current_location = frappe.db.get_value("Asset", asset.asset, "location")

		if not asset.source_location:
			if not current_location:
				frappe.throw(_("Source Location is required for the Asset {0}").format(asset.asset))
			else:
				asset.source_location = current_location
		else:
			if current_location != asset.source_location:
				frappe.throw(_("Asset {0} is currently located at {1}, not {2}.").
					format(asset.asset, current_location, asset.source_location))

	def validate_asset_issue(self, asset):
		if asset.target_location:
			frappe.throw(_("Issuing cannot be done to a location. \
				Please enter employee who has issued Asset {0}").
				format(asset.asset), title="Incorrect Movement Purpose")

		if not asset.to_employee:
			frappe.throw(_("Employee is required while issuing Asset {0}").format(asset.asset))

	def validate_asset_transfer(self, asset):
		if asset.to_employee:
			frappe.throw(_("Transferring cannot be done to an Employee. \
				Please enter location where Asset {0} has to be transferred").
				format(asset.asset), title="Incorrect Movement Purpose")

		if not asset.target_location:
			frappe.throw(_("Target Location is required while transferring Asset {0}").format(asset.asset))

		if asset.source_location == asset.target_location:
			frappe.throw(_("Source and Target Location cannot be same"))

	def validate_asset_receipt(self, asset):
		# only when asset is bought and first entry is made
		if not asset.source_location and not (asset.target_location or asset.to_employee):
			frappe.throw(_("Target Location or To Employee is required while receiving Asset {0}").format(asset.asset))

		elif asset.source_location:
			if asset.target_location and not asset.from_employee:
				frappe.throw(_("From employee is required while receiving Asset {0} at a target location").format(asset.asset))

			if asset.from_employee and not asset.target_location:
				frappe.throw(_("Target Location is required while receiving Asset {0} from an employee").format(asset.asset))

			if asset.to_employee and asset.target_location:
				frappe.throw(_("Asset {0} cannot be received at a location and \
					given to employee in a single movement").format(asset.asset))

	def validate_employee(self):
		for row in self.assets:
			if row.from_employee:
				self.validate_from_employee(row)

			if row.to_employee:
				self.validate_to_employee(row)

	def validate_from_employee(self, row):
		current_custodian = frappe.db.get_value("Asset", row.asset, "custodian")

		if current_custodian != row.from_employee:
			frappe.throw(_("Asset {0} currently belongs to {1}, not {2}.").
				format(row.asset, current_custodian, row.from_employee))

	def validate_to_employee(self, row):
		if frappe.db.get_value("Employee", row.to_employee, "company") != self.company:
			frappe.throw(_("Employee {0} does not belong to the company {1}").
				format(row.to_employee, self.company))