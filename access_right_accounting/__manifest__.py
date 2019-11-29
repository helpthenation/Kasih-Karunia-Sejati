# -*- coding: utf-8 -*-
{
    'name': "Access Right Accounting",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Waqas Yousaf",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full Purchase Access Rightlist
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','budget_std','account_accountant','budget_management','activity_based_budgetting','employee_expense_advance','vit_efaktur','account_followup'],

    # always loaded
    'data': [
        	'views/views.xml',
        	'views/templates.xml',
        	'security/emp_access_rights_accountung.xml',
        	'security/other_access.xml',
    	    'security/ir.model.access.csv',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}