# -*- coding: utf-8 -*-
{
    # Module Info.
    'name': "Aged Partner Balance Overdue",
    'category': 'Uncategorized',
    'version': '0.1',
    'summary': """Create new aging report""",
    'description': """Create new aging report""",

    # Author
    'author': "Hashmicro/Techultra/Nikesh",
    'website': "http://www.hashmicro.com",

    # Dependencies
    'depends': ['enterprise_accounting_report'],

    # Views
    'data': [
        'views/report_financial.xml',
    ],

    # Technical Specification
    'installable': True,
    'auto_install': False,
    'application': False,
}