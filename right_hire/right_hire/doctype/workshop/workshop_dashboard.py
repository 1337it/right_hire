from frappe import _

def get_data():
    return {
        'fieldname': 'workshop',
        'non_standard_fieldnames': {},
        'transactions': [
            {
                'label': _('Operations'),
                'items': ['Movements']
            }
        ]
    }
