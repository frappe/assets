# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import nowdate, add_days

from assets.asset.doctype.asset_.test_asset_ import (
	create_asset,
	create_company,
	create_asset_data,
)
from assets.asset.doctype.asset_maintenance_.asset_maintenance_ import calculate_next_due_date

class TestAssetMaintenance_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		create_maintenance_personnel()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_start_date_is_before_end_date(self):
		asset = create_asset(maintenance_required = 1, submit = 1)

		asset_maintenance = create_asset_maintenance(asset.name)
		asset_maintenance.asset_maintenance_tasks[0].start_date = nowdate()
		asset_maintenance.asset_maintenance_tasks[0].end_date = add_days(nowdate(), -1)

		self.assertRaises(frappe.ValidationError, asset_maintenance.save)

def create_maintenance_personnel():
	user_list = ["dwight@dm.com", "jim@dm.com", "pam@dm.com"]

	if not frappe.db.exists("Role", "Technician"):
		create_role("Technician")

	for user in user_list:
		if not frappe.db.get_value("User", user):
			create_user(user)

	if not frappe.db.exists("Asset Maintenance Team", "Team Dunder Mifflin"):
		create_maintenance_team(user_list)

def create_role(role_name):
	frappe.get_doc({
		"doctype": "Role",
		"role_name": role_name
	}).insert()

def create_user(user):
	frappe.get_doc({
		"doctype": "User",
		"email": user,
		"first_name": user,
		"new_password": "password",
		"roles": [{"doctype": "Has Role", "role": "Technician"}]
	}).insert()

def create_maintenance_team(user_list):
	frappe.get_doc({
		"doctype": "Asset Maintenance Team_",
		"maintenance_manager": "dwight@dm.com",
		"maintenance_team_name": "Team Dunder Mifflin",
		"company": "_Test Company",
		"maintenance_team_members": get_maintenance_team_members(user_list)
	}).insert()

def get_maintenance_team_members(user_list):
	maintenance_team_members = []

	for user in user_list[1:]:
		maintenance_team_members.append({
			"team_member": user,
			"full_name": user,
			"maintenance_role": "Technician"
		})

	return maintenance_team_members

def create_asset_maintenance(asset_name, num_of_assets=0, serial_no=None):
	asset_maintenance =	frappe.get_doc({
		"doctype": "Asset Maintenance_",
		"asset_name": asset_name,
		"num_of_assets": num_of_assets or (0 if serial_no else 1),
		"serial_no": serial_no,
		"maintenance_team": "Team Dunder Mifflin",
		"company": "_Test Company",
		"asset_maintenance_tasks": get_maintenance_tasks()
	}).insert(ignore_if_duplicate=True)

	return asset_maintenance

def get_maintenance_tasks():
	return [
		{
			"maintenance_task": "Antivirus Scan",
			"start_date": nowdate(),
			"periodicity": "Monthly",
			"maintenance_type": "Preventive Maintenance",
			"maintenance_status": "Planned",
			"assign_to": "jim@dm.com"
		},
		{
			"maintenance_task": "Check Gears",
			"start_date": nowdate(),
			"periodicity": "Yearly",
			"maintenance_type": "Calibration",
			"maintenance_status": "Planned",
			"assign_to": "pam@dm.com"
		}
	]
