# -*- coding: utf-8 -*-
{
    'name': "Customer Sales Team",

    'summary': """
        Customer Sales Details""",

    'description': """
    """,

    'author': "Hashmicro/GYB IT SOLUTIONS-Trivedi",
    'website': "http://www.hashmicro.com",

    'category': 'Account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'sales_team'],

    # always loaded
    'data': [
        'views/customer_partner_view.xml',
    ],
}
