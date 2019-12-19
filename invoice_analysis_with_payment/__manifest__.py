# -*- coding: utf-8 -*-
{
    "name": "Invoice Analysis With Payment",
    "author": "HashMicro/ Amit Patel",
    "version": "10.0.1.0",
    "website": "www.hashmicro.com",
    "category": "Accounting",
    'summary': 'Invoice Analysis With Payment',
    'description': """
    	This module cover the following points:

        * Add below fields in Invoice Analysis Report
            a. dimension : add invoice no & reference
            b. measure : add paid, amount due
            
        * Add Amount Paid column in customer invoice
    """,
    "depends": ['account'],
    "data": [
        "views/account_invoice_view.xml",
        "report/account_invoice_report_view.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
