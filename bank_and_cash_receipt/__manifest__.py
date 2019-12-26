# -*- coding: utf-8 -*-
{
    "name": "Bank and Cash Receipt",
    "summary": "Bank and Cash Receipt",
    'description': """

Bank and Cash Receipt

    """,
    'author': "Laxicon Solution",
    'website': "www.laxicon.in",
    "version": "10.0.1.0.0",
    "category": "Accounting",
    "depends": [
        'account_accountant','accounting_closing_period_std'
    ],
    "data": [
        'data/account_data.xml',
        'views/account_move_view.xml',
        'views/bukti_bank_keluar_view.xml',
        'views/bukti_bank_masuk_view.xml',
        'views/bukti_kas_keluar_view.xml',
        'views/bukti_kas_masuk_view.xml',
        'views/template.xml',   
        'wizard/bukti_bank_keluar_view.xml',
        'wizard/bukti_bank_masuk_view.xml',
        'wizard/bukti_kas_keluar_view.xml',
        'wizard/bukti_kas_masuk_view.xml',
        'report/bbm_template.xml',
        'report/bbk_template.xml',
        'report/bkk_template.xml',
        'report/bkm_template.xml'
    ],
    'sequence': 1,
    'installable': True,
    'auto_install': False,
    'application': True,
}
