# Copyright (c) 2024, Tridz Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TermsandConditionsTemplate(Document):
    def before_save(self):
        # Set created_by and created_on on first save
        if self.is_new():
            self.created_by = frappe.session.user
            self.created_on = frappe.utils.now()

        # Always update last_updated_by and last_updated_on
        self.last_updated_by = frappe.session.user
        self.last_updated_on = frappe.utils.now()
