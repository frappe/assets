# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class AssetActivity(Document):
	def validate(self):
		self.validate_activity_date()
		self.validate_serial_no()

	def validate_activity_date(self):
		purchase_date = frappe.db.get_value('Asset_', self.asset, 'purchase_date')

		if getdate(self.activity_date) < purchase_date:
			frappe.throw(_('Asset Activity cannot be performed before {0}').format(purchase_date))

	def validate_serial_no(self):
		is_serialized_asset = frappe.db.get_value('Asset_', self.asset, 'is_serialized_asset')

		if is_serialized_asset and not self.asset_serial_no:
			frappe.throw(_("Asset Serial No needs to be provided"))

def create_asset_activity(asset, activity_date, activity_type, reference_doctype, reference_docname, asset_serial_no=None, notes=None):
	asset_activity = frappe.get_doc({
		'doctype': 'Asset Activity',
		'asset': asset,
		'asset_serial_no': asset_serial_no,
		'activity_date': activity_date,
		'activity_type': activity_type,
		'reference_doctype': reference_doctype,
		'reference_docname': reference_docname,
		'notes': notes
	})
	asset_activity.submit()
