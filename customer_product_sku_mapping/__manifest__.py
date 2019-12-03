# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Product SKU",
    'summary': """
    		Product SKU : Sales > configuration > SKU \n
    		Product SKU : Inventory > configuration > SKU \n
    		Product SKU : Sales > Customer > SKU \n
    		
        """,
    'description': """
        Product SKU
    """,
    "version": "1.0",
    "category": "SKU",
    "author": "Hashmicro / Kunal Chavda",
    "website": "http://www.hashmicro.com",
    "depends": [
        'sales_team','stock','account',
    ],
    "data": [
        'views/sku_view.xml',
    ],
    "installable": True,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
