# -*- coding: utf-8 -*-
{
    "name": "Analytic Account Filter",
    "author": "HashMicro/ Amit Patel",
    "version": "10.0.1.0",
    "website": "www.hashmicro.com",
    "category": "Accounting",
    'summary': 'Analytic Account Filter',
    "description": """This module help to add Invoice Line Analytic Account in customer tree view and add filter for it.""",
    "depends": ["account","analytic"],
    "data": [
        "views/account_invoice_view.xml",
    ],
    'demo': [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
