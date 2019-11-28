# -*- coding: utf-8 -*-
{
    'name': 'Powerone Sync',
    'version': '1.0',
    'category': 'All Masters and Transaction',
    'author': 'Hashmicro/Antsyz-Muthulakshmi',
    'description': 'Data masters are manage by powerone and then send to odoo.',
    'website': 'www.hashmicro.com',
    'depends': ['base','sale','account'],
    'data': [
        'views/powerone_sync.xml',
        'views/sync_settings_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
