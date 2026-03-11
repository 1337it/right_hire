from frappe import _

def get_data():
    return {
        'fieldname': 'reservation',
        'non_standard_fieldnames': {},
        'transactions': [
            {
                'label': _('Agreements'),
                'items': ['Rental Agreement']
            }
        ]
    }
