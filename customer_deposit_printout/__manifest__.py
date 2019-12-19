# -*- coding: utf-8 -*-
{
    'name': 'Customer Deposit Report',
    'version': '1.0',
    'category': 'Accounting',
    'author': 'HashMicro/ MPTechnolabs - Vasant Chauhan',
    'website': "http://www.hashmicro.com",
    'summary': 'Customer Deposit Report',
    'depends': [
        'base', 'account', 'report', 'account_cancel', 'account_deposit'
    ],
    'data': [
       'views/account_report_view.xml',
       'views/account_report_layout_view.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
