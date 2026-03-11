from frappe import _

def get_data():
    return {
        'fieldname': 'lease_agreement',
        'non_standard_fieldnames': {
            'Movements': 'agreement_no',
        },
        'transactions': [
            {
                'label': _('Quotations'),
                'items': ['Lease Quotation']
            },
            {
                'label': _('Operations'),
                'items': ['Movements']
            },
            {
                'label': _('Fines & Tolls'),
                'items': ['Salik Transaction', 'Traffic Fine']
            }
        ]
    }
