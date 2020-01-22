# -*- coding: utf-8 -*-
{
    'name': "Unpaid Invoice List",

    'summary': """
        Unpaid Invoice details""",

    'description': """
        Generate Report Unpaid Invoice
    """,

    'author': "Hashmicro/GYB IT SOLUTIONS-Trivedi",
    'website': "http://www.hashmicro.com",

    'category': 'Account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_view.xml',
        'data/scheduler_sequence.xml',
        'report/unpaid_inv_report_view.xml',
        'report/report_menu.xml',
        'wizard/generate_unpaid_inv_wizard.xml',
        'views/unpaid_invoice_view.xml',
        'wizard/export_unpaid_invoice_view.xml',
    ],
}
