from frappe import _

def get_data():
    return {
        'fieldname': 'vehicle',
        'non_standard_fieldnames': {},
        'transactions': [
            {
                'label': _('Bookings'),
                'items': ['Lease Agreement', 'Rental Agreement']
            },
            {
                'label': _('Operations'),
                'items': ['Movements']
            },
            {
                'label': _('Fines & Tolls'),
                'items': ['Salik Transaction', 'Traffic Fine']
            },
        ]
    }
