import time
from datetime import datetime
import tempfile
import binascii
import xlrd
import base64
import odoo
import odoo.modules
from datetime import date, datetime
from odoo.exceptions import Warning, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import models, fields, exceptions, api, _

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


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _default_bank_statement(self):

        attachment_obj = self.env['ir.attachment'].sudo()

        path = odoo.modules.get_module_resource('Bank_statement_import')
        path = path + '/static/src/Bank_Import.xlsx'

        with open(path,
                  "rb") as xls_file:
            report_name = 'Bank_Import'
            filename = "%s.%s" % (report_name, "xlsx")
            attachment = attachment_obj.search([('name', '=', filename)], limit=1)
            if not attachment:
                attachment = attachment_obj.create({
                    'name': filename,
                    'datas': base64.b64encode(xls_file.read()),
                    'datas_fname': filename,
                    'res_model': 'ir.ui.view',
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                    'public': True,
                })
            return attachment.id

    def _default_bank_statement_binary(self):

        path = odoo.modules.get_module_resource('Bank_statement_import')
        path = path + '/static/src/Bank_Import.xlsx'

        with open(path,
                  "rb") as xls_file:
            report_name = 'Bank_Import'
            filename = "%s.%s" % (report_name, "xlsx")
            default_bank_statement = base64.b64encode(xls_file.read())

            return default_bank_statement

    attachment_id = fields.Many2one('ir.attachment', string="Sample Bank Statement", default=_default_bank_statement)
    default_bank_statement = fields.Binary(string="Sample Bank Statement", related="attachment_id.datas")

    @api.multi
    def find_partner(self, name):
        partner_obj = self.env['res.partner']
        partner_search = partner_obj.search([('name', '=', name)], limit=1)
        if partner_search:
            return partner_search
        else:
            partner_id = partner_obj.create({
                'name': name})
            return partner_id

    @api.multi
    def import_bank_statement_file(self):
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.data_file))
        fp.seek(0)

        bank_obj = self.env['account.bank.statement']

        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        values = {}
        lines = []
        for row_no in range(sheet.nrows):
            if row_no == 5 or row_no == 6:
                fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
            else:
                line = (
                    map(lambda row: isinstance(row.value, unicode) and row.value.encode('utf-8') or str(row.value),
                        sheet.row(row_no)))
                if row_no == 0:
                    values.update({
                        'name': line[1],
                    })
                if row_no == 1:
                    journal_id = self.env['account.journal'].search([('code', '=', line[1])])
                    values.update({
                        'journal_id': journal_id.id,
                    })
                if row_no == 2:
                    # a1 = int(float(line[1]))
                    # a1_as_datetime = datetime(*xlrd.xldate_as_tuple(a1, workbook.datemode))
                    date_string = datetime.strptime(line[1], '%d/%m/%Y')
                    values.update({
                        'date': date_string,
                    })

                if row_no == 3:
                    values.update({
                        'balance_start': float(line[1]),
                    })

                if row_no == 4:
                    values.update({
                        'balance_end_real': float(line[1]),
                    })

                if row_no >= 7:
                    a1 = int(float(line[0]))
                    a1_as_datetime = datetime(*xlrd.xldate_as_tuple(a1, workbook.datemode))
                    date_string = a1_as_datetime.date().strftime('%Y-%m-%d')
                    partner_id = False
                    if line[2]:
                        partner_id = self.find_partner(line[2]).id

                    lines.append((0, 0, {
                        'date': date_string,
                        'name': line[1],
                        'amount': line[3],
                        'partner': partner_id,
                    }))
        values['line_ids'] = lines
        bank_id = False
        if values:
            bank_statement_id = bank_obj.search([('name', '=', values['name'])], limit=1)
            if bank_statement_id:
                raise UserError(
                    _('%s Bank Account Statement Is Already Exist') % (
                        values['name'],))
            else:
                bank_id = bank_obj.create(values)
        else:
            raise UserError(
                _('%s Bank Account Statement Values Are Not Found'))
        if bank_id:
            return {
                'name': _('Bank Statements'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.bank.statement',
                'res_id': bank_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'context': {}
            }
