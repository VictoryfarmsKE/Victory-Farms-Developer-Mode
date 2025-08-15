app_name = "victoryfarmsdeveloper"
app_title = "VictoryFarmsDeveloper"
app_publisher = "Christine K"
app_description = "VictoryFarmsDeveloper"
app_email = "christinek@victoryfarmskenya.com"
app_license = "mit"
app_include = ["erpnext"]
required_apps = ["frappe", "erpnext"]

fixtures = [
    "Client Script",
    "Server Script",
    "Custom Field",
    {"dt": "Client Script", "filters": [["module", "like", "VictoryFarmsDeveloper"]]},
    {"dt": "Server Script", "filters": [["module", "like", "VictoryFarmsDeveloper"]]},
    {"dt": "Custom Field", "filters": [["module", "like", "VictoryFarmsDeveloper"]]},
]


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/victoryfarmsdeveloper/css/victoryfarmsdeveloper.css"
# app_include_js = "/assets/victoryfarmsdeveloper/js/victoryfarmsdeveloper.js"

# include js, css files in header of web template
# web_include_css = "/assets/victoryfarmsdeveloper/css/victoryfarmsdeveloper.css"
# web_include_js = "/assets/victoryfarmsdeveloper/js/victoryfarmsdeveloper.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "victoryfarmsdeveloper/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}
app_include_js = [
    "/assets/victoryfarmsdeveloper/js/stock_entry.js"
]

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
    "Stock Entry": "victoryfarmsdeveloper/customization/stock_entry_item_break_down/stock_entry_item_break_down.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
doctype_list_js = {
    "Leave Application" : "public/js/leave_application_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "victoryfarmsdeveloper/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "victoryfarmsdeveloper.utils.jinja_methods",
# 	"filters": "victoryfarmsdeveloper.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "victoryfarmsdeveloper.install.before_install"
# after_install = "victoryfarmsdeveloper.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "victoryfarmsdeveloper.uninstall.before_uninstall"
# after_uninstall = "victoryfarmsdeveloper.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "victoryfarmsdeveloper.utils.before_app_install"
# after_app_install = "victoryfarmsdeveloper.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "victoryfarmsdeveloper.utils.before_app_uninstall"
# after_app_uninstall = "victoryfarmsdeveloper.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "victoryfarmsdeveloper.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

permission_query_conditions = {
    "Appraisal": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.appraisal.appraisal.get_permission_query_conditions"
    # "Department Appraisal": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.department_appraisal.department_appraisal.get_permission_query_conditions"

}

has_permission = {
    "Appraisal": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.appraisal.appraisal.has_permission"
    # "Department Appraisal": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.department_appraisal.department_appraisal.has_permission"

}
# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }
override_doctype_class = {
    "Stock Entry": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.stock_entry.stock_entry.CustomStockEntry",
    "Appraisal Cycle": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.appraisal_cycle.appraisal_cycle.CustomAppraisalCycle"
    # "Leave Application": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.leave_application.leave_application.CustomLeaveApplication"
}
# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
# doc_events = {
#     "Stock Entry": {
#         "on_submit": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.stock_entry.stock_entry.on_submit"
#     }
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"victoryfarmsdeveloper.tasks.all"
# 	],
# 	"daily": [
# 		"victoryfarmsdeveloper.tasks.daily"
# 	],
# 	"hourly": [
# 		"victoryfarmsdeveloper.tasks.hourly"
# 	],
# 	"weekly": [
# 		"victoryfarmsdeveloper.tasks.weekly"
# 	],
# 	"monthly": [
# 		"victoryfarmsdeveloper.tasks.monthly"
# 	],
# }

scheduler_events = {
    "daily": [
        "victoryfarmsdeveloper.notifications.check_low_stock.check_low_stock"
    ],
    "hourly": [
        "victoryfarmsdeveloper.notifications.leave_balance_update_check.process_checkins_without_shift"
    ],
    "cron": {
        "0 7 * * *": [
            "victoryfarmsdeveloper.notifications.leave_balance_update_check.leave_balance_update_check"
        ],
        "0 23 * * *": [
            "victoryfarmsdeveloper.notifications.po_pending_approval.send_pending_po_notifications"
        ],
        "0 12,15 * * *": [
            "victoryfarmsdeveloper.notifications.check_low_stock.check_branch_low_stock"
        ],
        "0 0 1 * *": [
            "victoryfarmsdeveloper.notifications.leave_balance_update_check.create_long_weekend_leave_allocation"
        ],
        "30 8 25-31 * *": [
            "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.appraisal.send_pending_appraisal_notifications"
        ]
    }
}


doc_events = {
    "Sales Invoice": {
        "on_change": "victoryfarmsdeveloper.notifications.sales_invoice_status_change.sales_invoice_status_change"
    },
    "Purchase Order": {
        "on_update": "victoryfarmsdeveloper.notifications.po_pending_approval.send_po_approved_notification"
    },
    "Stock Entry": {
        "before_save": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.stock_entry.stock_entry.before_save_stock_entry",
        "before_submit": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.stock_entry.stock_entry.before_submit_stock_entry"
    }
}


# Testing
# -------

# before_tests = "victoryfarmsdeveloper.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "victoryfarmsdeveloper.event.get_events"
# }
override_whitelisted_methods = {
    "erpnext.stock.doctype.stock_entry.stock_entry.make_stock_in_entry": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.stock_entry.stock_entry.make_stock_in_entry"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "victoryfarmsdeveloper.task.get_dashboard_data"
# }
# override_doctype_dashboards = {
#     "Purchase Order": "victoryfarmsdeveloper.victoryfarmsdeveloper.customization.purchase_order.purchase_order_dashboard.get_data"
# }
# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["victoryfarmsdeveloper.utils.before_request"]
# after_request = ["victoryfarmsdeveloper.utils.after_request"]

# Job Events
# ----------
# before_job = ["victoryfarmsdeveloper.utils.before_job"]
# after_job = ["victoryfarmsdeveloper.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"victoryfarmsdeveloper.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

