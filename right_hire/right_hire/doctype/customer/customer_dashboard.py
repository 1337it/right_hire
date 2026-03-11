from frappe import _

def get_data():
    return {
        'fieldname': 'customer',
        'non_standard_fieldnames': {
            'Movements': 'out_customer',
        },
        'transactions': [
            {
                'label': _('Bookings'),
                'items': ['Reservation', 'Rental Agreement', 'Lease Agreement', 'Lease to Own']
            },
            {
                'label': _('Quotations'),
                'items': ['Lease Quotation', 'Lease to Own Quotation']
            },
            {
                'label': _('Operations'),
                'items': ['Movements']
            },
            {
                'label': _('Drivers'),
                'items': ['Driver']
            },
            {
                'label': _('Violations'),
                'items': ['Violation']
            },
            {
                'label': _('Billing'),
                'items': ['Invoice']
            }
        ]
    }
