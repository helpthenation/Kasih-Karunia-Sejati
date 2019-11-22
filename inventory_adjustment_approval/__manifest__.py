# -*- coding: utf-8 -*-
{
    'name' : 'Inventory Adjustment Approval',
    'version' : '1.0',
    'category': 'Inventory',
    'author': 'HashMicro / MP technolabs(Chankya)',
    'description': """
        This module will modify Inventory adjustment approval flow.
    """,
    'website': 'www.hashmicro.com',
    'depends' : ['hr','stock_account'],
    'data': [
        'views/stock_inventory_view.xml',
    ],
    'demo': [
    ],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
