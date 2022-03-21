# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import frappe
import unittest

from assets.asset.doctype.asset_.test_asset_ import (
	create_company,
	create_asset_data,
)

class TestAssetMaintenance_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		create_maintenance_personnel()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

def create_maintenance_personnel():
	user_list = ["dwight@dm.com", "jim@dm.com", "stanley@dm.com"]

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