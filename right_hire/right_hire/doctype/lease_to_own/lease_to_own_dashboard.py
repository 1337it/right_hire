from frappe import _

def get_data():
    return {
        'fieldname': 'lease_to_own',
        'non_standard_fieldnames': {},
        'transactions': [
            {
                'label': _('Quotations'),
                'items': ['Lease to Own Quotation']
            }
        ]
    }
