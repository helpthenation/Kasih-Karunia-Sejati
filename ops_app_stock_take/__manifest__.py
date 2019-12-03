# -*- coding: utf-8 -*-
{
    'name': 'Ops App Integration - Stock Take',
    'version': '1.0',
    'category': 'Stock API',
    'sequence': 10,
    'summary': '',
    'description': '''Stock module will be installed automatically and allow the Ops mobile app integration to access the Equip System to do the following functionality.
    - Inventory Adjustment
    - Stock Take
    ''',
    'website': 'http://www.hashmicro.com/',
    'author': 'Hashmicro/ AntsyZ - Goutham',
    'depends': [
        'stock'
    ],
    'data': [
        'data/stock_count_sequence.xml',
        'security/ir.model.access.csv',
        'views/stock_count_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}