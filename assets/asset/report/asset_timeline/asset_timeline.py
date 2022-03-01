# Copyright (c) 2022, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def get_columns():
	columns = [
		{
			"label": _("Activity Date"),
			"fieldtype": "Date",
			"fieldname": "activity_date",
			"width": 200
		},
		{
			"label": _("Activity Type"),
			"fieldtype": "Data",
			"fieldname": "activity_type",
			"width": 200
		},
		{
			"label": _("Reference Document Type"),
			"fieldtype": "Link",
			"fieldname": "reference_doctype",
			"options": "DocType",
			"width": 200
		},
		{
			"label": _("Reference Document Name"),
			"fieldtype": "Dynamic Link",
			"fieldname": "reference_docname",
			"options": "reference_doctype",
			"width": 200
		},
		{
			"label": _("Notes"),
			"fieldtype": "Small Text",
			"fieldname": "notes",
			"width": 400
		}
	]

	return columns

def get_data(filters):
	asset_activities = []

	fields = get_fields()

	asset_activities = frappe.get_all(
		"Asset Activity",
		filters = filters,
		fields = fields,
		order_by = "activity_date"
	)

	return asset_activities

def get_fields():
	return ["activity_type", "activity_date", "reference_doctype", "reference_docname", "notes"]