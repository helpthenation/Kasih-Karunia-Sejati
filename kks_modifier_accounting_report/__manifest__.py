# -*- coding: utf-8 -*-
{
    'name': "kks_modifier_accounting_report",
    'summary': "Modifier Accounting Report",
    'description': "Accounting Reports",
    'author': "HashMicro / Kinjal",
    'website': "www.hashmicro.com",
    'category': 'account',
    'version': '1.0',
    'depends': [
        'account_accountant', 'enterprise_accounting_report'
    ],
    'data': [
    ],
    'qweb': [
        'static/src/xml/account_report_backend.xml',
    ],
    'installable': True,
    'auto_install': False,
}
