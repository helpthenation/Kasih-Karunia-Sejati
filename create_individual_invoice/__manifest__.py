# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################
{
    'name': "So to Invoice One by One",

    'summary': """
        Create Invoice One by One
        """,
    'description': """
        Create Invoice One by One
    """,
    'author': "PT HashMicro Solusi Indonesia",
    'website': "http://www.hashmicro.com",

    'category': 'Uncategorized',
    'version': '10.1',

    'depends': [
        'base',
        'sale',
    ],
    'data': [
        'wizard/sale_make_invoice_onebyone_advance_views.xml',
    ],
}
