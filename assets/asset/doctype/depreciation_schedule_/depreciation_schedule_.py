# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from assets.controllers.base_asset import validate_serial_no

class DepreciationSchedule_(Document):
	def validate(self):
		validate_serial_no(self)
