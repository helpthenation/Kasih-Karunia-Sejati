# -*- coding: utf-8 -*-
{
    'name': "Approving Matrix Credit Limit",
    'description': """
        Approving Matrix Credit Limit
    """,
    'author': "HashMicro/Pravin",
    'website': "http://www.hashmicro.com",
    'category': 'Sale',
    'version': '1.2',
    'depends': ['base','mail', 'account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/credit_limit_wizard_view.xml',
        'views/account_config_settings.xml',
        'views/over_credit_approving_matrix_views.xml',
        'views/sale_order_views.xml',
    ],
    'demo': [
    ],
}
