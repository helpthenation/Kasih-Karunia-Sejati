# -*- coding: utf-8 -*-
{
    'name': "sales_check",

    'summary': """
        checking process in sales before create invoice (similar to bank reconciliation process) """,

    "author": "Hashmicro/ Balaji(Antsyz)",
    "website": "www.hashmicro.com",
    'category': 'sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['customer_product_sku_mapping',
                'account'],

    # always loaded
    'data': [
        'data/sales_check_data.xml',
        'views/sales_check_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    "installable": True,
    "auto_install": False,
}