# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################
{
    'name': "Create Purchase Invoice Wiz",

    'summary': """
        Create Purchase Invoice Wiz
        """,
    'description': """
        Create Purchase Invoice Wiz
    """,
    'author': "PT HashMicro Solusi Indonesia",
    'website': "http://www.hashmicro.com",

    'category': 'Uncategorized',
    'version': '10.1',

    'depends': [
        'base',
        'purchase',
        'account',
    ],
    'data': [
        'wizard/purchase_to_invoice_advance_views.xml',
    ],
}
