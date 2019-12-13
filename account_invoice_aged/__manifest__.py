# -*- coding: utf-8 -*-
{
    'name': "Account Invoice Aged",

    'summary': """
        Account Invoice details""",

    'description': """
    """,

    'author': "Hashmicro/GYB IT SOLUTIONS-Trivedi",
    'website': "http://www.hashmicro.com",

    'category': 'Account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account'],

    # always loaded
    'data': [
        'views/account_invoice_view.xml',
    ],
}
