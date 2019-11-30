# -*- coding: utf-8 -*-
{
    'name': "Payment Plan",

    'summary': """
        Payment plan details""",

    'description': """
        Generate Report Payment Plan
    """,

    'author': "Jaydeep",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/10.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['account', 'purchase'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/sequence_view.xml',
        'data/scheduler_sequence.xml',
        'report/payment_report_view.xml',
        'report/report_menu.xml',
        'wizard/generate_payment_view.xml',
        'views/payment_plan_views.xml',
    ],
}