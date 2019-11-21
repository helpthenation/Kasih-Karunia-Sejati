# -*- coding: utf-8 -*-
{
    'name': "Customer Invoice Status",

    'summary': """
        Change Invoice Status""",

    'description': """
        Based On the Due date change the Invoice Status
    """,

    'author': "Jaydeep",
    'website': "http://www.hashmicro.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['account'],
    
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
    ],
    
}