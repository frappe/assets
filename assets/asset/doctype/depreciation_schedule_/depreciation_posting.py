import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)


def post_all_depreciation_entries(date=None):
	# Return if automatic booking of asset depreciation is disabled
	if not cint(frappe.db.get_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically")):
		return

	if not date:
		date = today()

	for schedule in get_schedules_that_need_posting(date):
		post_depreciation_entries(schedule, date)
		frappe.db.commit()

def get_schedules_that_need_posting(date):
	active_schedules = frappe.get_all(
		"Depreciation Schedule_",
		filters = {
			"status": "Active"
		},
		pluck = "name"
	)

	schedules_that_need_posting = frappe.get_all(
		"Asset Depreciation Schedule",
		filters = {
			"parent": ["in", active_schedules],
			"schedule_date": ["<=", date],
			"depreciation_entry": None
		},
		pluck = "parent"
	)

	# to remove duplicates
	schedules_that_need_posting = list(set(schedules_that_need_posting))

	return schedules_that_need_posting

@frappe.whitelist()
def post_depreciation_entries(schedule_name, date=None):
	frappe.has_permission("Depreciation Entry", throw=True)

	if not date:
		date = today()

	depr_schedule = frappe.get_doc("Depreciation Schedule_", schedule_name)
	asset = frappe.get_doc("Asset_", depr_schedule.asset)

	credit_account, debit_account = get_depreciation_accounts(asset.asset_category, asset.company)

	depreciation_cost_center, depreciation_series = get_depreciation_details(asset.company)

	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	decrease_in_value = 0

	for schedule in depr_schedule.depreciation_schedule:
		if not schedule.journal_entry and getdate(schedule.schedule_date) <= getdate(date):
			depr_entry = make_depreciation_entry(depreciation_series, schedule, depr_schedule, asset,
				credit_account, debit_account, depreciation_cost_center, accounting_dimensions)

			schedule.db_set("depreciation_entry", depr_entry.name)
			decrease_in_value += schedule.depreciation_amount

	parent = get_parent(depr_schedule, asset)
	update_asset_value_in_parent(parent, depr_schedule.finance_book, decrease_in_value)
	parent.set_status()

@frappe.whitelist()
def get_depreciation_accounts(asset_category, company):
	accumulated_depreciation_account = depreciation_expense_account = None

	accumulated_depreciation_account, depreciation_expense_account = \
		get_depreciation_accounts_from_asset_category(asset_category, company)

	if not accumulated_depreciation_account or not depreciation_expense_account:
		accumulated_depreciation_account, depreciation_expense_account = \
			get_depreciation_accounts_from_company(company, accumulated_depreciation_account,
				depreciation_expense_account)

	if not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}")
			.format(asset_category, company))

	credit_account, debit_account = get_credit_and_debit_accounts(
		accumulated_depreciation_account, depreciation_expense_account)

	return credit_account, debit_account

def get_depreciation_accounts_from_asset_category(asset_category, company):
	return frappe.db.get_value(
		"Asset Category Account",
		filters = {
			"parent": asset_category,
			"company_name": company
		},
		fieldname = ["accumulated_depreciation_account", "depreciation_expense_account"]
	)

def get_depreciation_accounts_from_company(company, accumulated_depreciation_account, depreciation_expense_account):
	accounts = frappe.get_cached_value(
		"Company",
		company,
		["accumulated_depreciation_account", "depreciation_expense_account"]
	)

	if not accumulated_depreciation_account:
		accumulated_depreciation_account = accounts[0]
	if not depreciation_expense_account:
		depreciation_expense_account = accounts[1]

	return accumulated_depreciation_account, depreciation_expense_account

def get_credit_and_debit_accounts(accumulated_depreciation_account, depreciation_expense_account):
	root_type = frappe.get_value("Account", depreciation_expense_account, "root_type")

	if root_type == "Expense":
		credit_account = accumulated_depreciation_account
		debit_account = depreciation_expense_account
	elif root_type == "Income":
		credit_account = depreciation_expense_account
		debit_account = accumulated_depreciation_account
	else:
		frappe.throw(_("Depreciation Expense Account should be an Income or Expense Account."))

	return credit_account, debit_account

def get_depreciation_details(company):
	return frappe.get_cached_value(
		"Company",
		company,
		["depreciation_cost_center", "series_for_depreciation_entry"]
	)

def make_depreciation_entry(depreciation_series, schedule_row, depr_schedule, asset, credit_account,
	debit_account, depreciation_cost_center, accounting_dimensions):
	depr_entry = frappe.new_doc("Depreciation Entry")
	depr_entry.update({
		"naming_series": depreciation_series,
		"posting_date": schedule_row.schedule_date,
		"company": asset.company,
		"asset": depr_schedule.asset,
		"serial_no": depr_schedule.serial_no,
		"finance_book": depr_schedule.finance_book,
		"credit_account": credit_account,
		"debit_account": debit_account,
		"depreciation_amount": schedule_row.depreciation_amount,
		"cost_center": depreciation_cost_center,
		"reference_doctype": depr_schedule.doctype,
		"reference_docname": depr_schedule.name,
		"depr_schedule_row": schedule_row.name
	})

	add_accounting_dimensions(accounting_dimensions, depr_entry, asset)

	depr_entry.flags.ignore_permissions = True
	depr_entry.save()
	depr_entry.submit()

	return depr_entry

def add_accounting_dimensions(accounting_dimensions, depr_entry, asset):
	for dimension in accounting_dimensions:
		if (asset.get(dimension['fieldname']) or dimension.get('mandatory_for_bs') or dimension.get('mandatory_for_pl')):
			depr_entry.update({
				dimension['fieldname']: asset.get(dimension['fieldname']) or dimension.get('default_dimension')
			})

def get_parent(depr_schedule, asset):
	if depr_schedule.serial_no:
		parent = frappe.get_doc("Asset Serial No", depr_schedule.serial_no)
	else:
		parent = asset

	return parent

def update_asset_value_in_parent(parent, finance_book, decrease_in_value):
	for fb in parent.get("finance_books"):
		if fb.finance_book == finance_book:
			fb.asset_value -= decrease_in_value
			break

	parent.update_asset_value()
