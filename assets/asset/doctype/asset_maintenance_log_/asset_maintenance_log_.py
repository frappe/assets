# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class AssetMaintenanceLog_(Document):
	def validate(self):
		self.check_if_maintenance_is_overdue()
		self.validate_completion_date()

	def on_submit(self):
		self.validate_maintenance_status()

	def check_if_maintenance_is_overdue(self):
		if getdate(self.due_date) < getdate() and self.maintenance_status not in ["Completed", "Cancelled"]:
			self.maintenance_status = "Overdue"

	def validate_completion_date(self):
		if self.maintenance_status == "Completed" and not self.completion_date:
			frappe.throw(_("Please select Completion Date for Completed Asset Maintenance Log"))

		if self.maintenance_status != "Completed" and self.completion_date:
			frappe.throw(_("Please select Maintenance Status as Completed or remove Completion Date"))

	def validate_maintenance_status(self):
		if self.maintenance_status not in ["Completed", "Cancelled"]:
			frappe.throw(_("Maintenance Status has to be Cancelled or Completed to Submit this doc"))