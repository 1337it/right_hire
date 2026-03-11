import frappe
from frappe import _

no_cache = 1

def get_context(context):
    # Frappe handles the login redirect automatically when PermissionError is raised
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to access the Customer Portal"), frappe.PermissionError)

    customer = frappe.db.get_value(
        "Customer",
        {"email": frappe.session.user},
        ["name", "customer_name", "account_id"],
        as_dict=True,
    )

    if not customer:
        context.customer_name = ""
        context.account_id = ""
        context.no_customer = True
        return

    context.customer_name = customer.customer_name
    context.account_id = customer.account_id or ""
    context.no_customer = False
