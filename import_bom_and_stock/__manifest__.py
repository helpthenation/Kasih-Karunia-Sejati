# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 BrowseInfo(<http://www.browseinfo.in>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Import BOM and Stock',
    'version': '1.1',
    'sequence': 4,
    'summary': 'This module helps to import stock and BOM using excel file',
    'category' : 'Warehouse',
    'description': """
    """,
    'author': 'Hashmicro/ Janbaz Aga/ Jaydeep',
    'website': 'www.hashmicro.com',
    'depends': ['base','stock','mrp','product_expiry_notification'],
    'data': [
        "views/stock_view.xml",
        "wizard/xls_report_wizard.xml",
        "wizard/report_download_test.xml",
        "wizard/import_bom_view.xml",
     ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    "images":[""],
}
