# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class AssetMaintenance_(Document):
	def validate(self):
		self.validate_tasks()

	def validate_tasks(self):
		for task in self.get("asset_maintenance_tasks"):
			self.validate_start_date(task)
			self.check_if_task_is_overdue(task)
			self.validate_assignee(task)

	def validate_start_date(self, task):
		if task.end_date and (getdate(task.start_date) >= getdate(task.end_date)):
			frappe.throw(_("Row #{0}: Start Date should be before End Date for task {1}")
				.format(task.idx, task.maintenance_task))

	def check_if_task_is_overdue(self, task):
		if getdate(task.next_due_date) < getdate():
			task.maintenance_status = "Overdue"

	def validate_assignee(self, task):
		if not task.assign_to and self.docstatus == 0:
			frappe.throw(_("Row #{0}: Please asign task {1} to a team member.")
				.format(task.idx, task.maintenance_task))

