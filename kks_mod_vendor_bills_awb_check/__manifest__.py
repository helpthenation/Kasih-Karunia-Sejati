# -*- coding: utf-8 -*-
{
    'name': "KKS Mod Vendor Bills AWB Check",

    'summary': """
        checking process in purchases before create bills (similar to bank reconciliation process) """,

    "author": "Hashmicro/ GYB IT SOLUTIONS-Trivedi",
    "website": "www.hashmicro.com",
    'category': 'account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account','purchase'],#'customer_product_sku_mapping',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/vendor_bill_check_data.xml',
        'views/vendor_bill_check_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    "installable": True,
    "auto_install": False,
}
