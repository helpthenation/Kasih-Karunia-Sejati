# -*- coding: utf-8 -*-

from odoo import fields, models
import base64

        
class ExportUnpaidInvoice(models.TransientModel):
    _name = 'export.unpaid.invoice'
    
    excel_file = fields.Binary(string='Excel File')
    file_name = fields.Char(string='Txt File', size=64)
