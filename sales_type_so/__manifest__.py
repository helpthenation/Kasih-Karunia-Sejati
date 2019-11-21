# -*- coding: utf-8 -*-
{
    "name": "Sales Type SO",
    "author": "HashMicro/ Amit Patel",
    "version": "10.0.1.0",
    "website": "www.hashmicro.com",
    "category": "Sale",
    'summary': 'Sales Type in Sales Order',
    "description": """This module help to make configuration for Sales Type and add Sales Type selection in Sales Order.""",
    "depends": ["sale","sales_team"],
    "data": [
        "security/ir.model.access.csv",
        "views/sales_type_view.xml",
    ],
    'demo': [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
