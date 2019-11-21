{
    "name": "Stock Adjustment Specific Date",
    "category": 'Stock',
    'summary': '',
    'version' : '1.1',
    "description": """
        A new menu will be added in the Configuration and a new Excel report is created
    """,
    "author": "Hashmicro/Arjun/Jaydeep",
    "website": "http://hashmicro.com/",
    "depends": ['base', 'stock','report_xlsx',
                'Add_Column_Theoritical Amount_and_Real Amount_in_Inventory Adjustment',
                'full_inv_adjustment', 'stock_account'],
    "data": [
        'security/ir.model.access.csv',
        'report/report.xml',
        'views/stock_custom_view.xml',
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}