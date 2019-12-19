# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2015-Today BrowseInfo (<http://www.browseinfo.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from openerp.exceptions import Warning
from openerp import models, fields, exceptions, api, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from xlrd import open_workbook
import xmlrpclib
import xlrd
import os
import tempfile
import binascii
from xlwt import Workbook
import xlwt

try:
    import xmlrpclib
except ImportError:
    _logger.debug('Cannot `import xmlrpclib`.')

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')
# for xls
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')


class gen_inv(models.TransientModel):
    _name = "stock.import"

    file = fields.Binary('File')
    inv_name = fields.Char('Inventory Name')
    location_id = fields.Many2one('stock.location', "Location")

    @api.multi
    def import_xls(self):

        """Load Inventory data from the CSV file."""
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file))
        fp.seek(0)
        values = {}
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        inventory_id = self.env['stock.inventory'].create({'name': self.inv_name})
        product_obj = self.env['product.product']
        stock_lot_obj = self.env['stock.production.lot']

        for row_no in range(sheet.nrows):
            val = {}
            if row_no <= 0:
                fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
            else:
                line = (
                map(lambda row: isinstance(row.value, unicode) and row.value.encode('utf-8') or str(row.value),
                    sheet.row(row_no)))
                if line:
                    values.update({'code': line[0], 'quantity': line[1], 'UOM': line[2], 'lot': line[3],'exp_date':line[4]})

                    prod_lst = product_obj.search([('default_code', '=',
                                                    values['code'])])
                    if prod_lst:
                        val['product'] = prod_lst[0].id
                        val['quantity'] = values['quantity']
                        val['UOM'] = values['UOM']
                        val['lot'] = values['lot']
                        val['exp_date'] = values['exp_date']
                    if bool(val):
                        # product_uom_id=product_obj.browse(val['product']).uom_id
                        product_uom_obj = self.env['product.uom']
                        product_uom_id = product_uom_obj.search([('name', '=', val['UOM'])])
                        if not product_uom_id:
                            raise UserError(_('"%s" Product UOM category is not available.') % (val['UOM']))

                        lot_id = stock_lot_obj.search(
                            [('product_id', '=', val['product']), ('name', '=', val['lot'])])
                        for lot in lot_id:
                            lot_obj = stock_lot_obj.browse(lot_id)

                        if not lot_id:
                            lot = stock_lot_obj.create({'name': val['lot'],
                                                        'product_id': val['product'],
                                                        'life_end':val['exp_date']})
                            lot_id = lot

                        res = inventory_id.write({
                            'line_ids': [(0, 0, {'product_id': val['product'], 'location_id': self.location_id.id,
                                                 'product_uom_id': product_uom_id.id,
                                                 'product_qty': val['quantity'], 'prod_lot_id': lot_id.id})]})
                    else:
                        continue
        res = self.env['stock.inventory'].with_context(ids=inventory_id).prepare_inventory()
        return res


#
class stock_inventory(models.Model):
    _inherit = "stock.inventory"

    @api.multi
    def action_start(self):
        if self._context.get('ids'):
            self = self._context.get('ids')
            for inventory in self:
                vals = {'state': 'confirm', 'date': fields.Datetime.now()}
                if (inventory.filter != 'partial') and not inventory.line_ids:
                    vals.update({'line_ids': [(0, 0, line_values) for line_values in inventory.line_ids]})
                inventory.write(vals)
        else:
            super(stock_inventory, self).action_start()
        return True

    prepare_inventory = action_start

