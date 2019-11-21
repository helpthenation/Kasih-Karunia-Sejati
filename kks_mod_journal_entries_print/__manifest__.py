{
    "name": "KKS Modifier Journal Entries",
    "category": 'Accounting',
    'summary': '',
    "description": """
        Modifies Journal Entry 
    """,
    "sequence": 4,
    "author": "Hashmicro/Arjun",
    "website": "http://hashmicro.com/",
    "depends": ['base','account','journal_entries_print'],
    "data": [
        'views/accounting_journal_entry_view.xml',
        'report/journal_entry_report.xml',
        # 'security/crm_group.xml',
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}