from frappe import _

def get_data():
    return {
        'fieldname': 'parent_movement',
        'non_standard_fieldnames': {
            'Movements': 'parent_movement'
        },
        'transactions': [
            {
                'label': _('Linked Movements'),
                'items': ['Movements']
            }
        ]
    }
