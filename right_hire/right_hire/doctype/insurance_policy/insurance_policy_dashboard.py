from frappe import _

def get_data():
    return {
        'fieldname': 'insurance_policy',
        'non_standard_fieldnames': {},
        'transactions': [
            {
                'label': _('Vehicles'),
                'items': ['Vehicle']
            }
        ]
    }
