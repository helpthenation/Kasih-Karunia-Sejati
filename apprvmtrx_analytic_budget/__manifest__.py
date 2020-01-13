# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################
{
    'name': "Approving Matrix Analitic Budget",

    'summary': """
        Create Approving Matrix Analitic Budget
    """,
    'description': """
        Create Approving Matrix Analitic Budget
    """,
    'author': "PT HashMicro Solusi Indonesia",
    'website': "http://www.hashmicro.com",

    'category': 'Uncategorized',
    'version': '10.1',

    'depends': ['base', 'account', 'analytic', 'account_budget', 'budget_management_extension'],

    'data': [
        'views/analytic_account_views.xml',
        'views/inherit_analytic_views.xml',
        'views/approving_matrix_view.xml',
    ],
}
