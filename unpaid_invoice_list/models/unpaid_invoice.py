# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import xlwt
from cStringIO import StringIO
import base64
import calendar
import time

class UnpaidInvoice(models.Model):
    _name = 'unpaid.invoice'

    name = fields.Char('Name')
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('unpaid.invoice') or '/'
        return super(UnpaidInvoice, self).create(vals)

    owner = fields.Many2one('res.users', string='Created By')
    payment_date = fields.Date('Collection Date')
    memo = fields.Char('Memo')
    unpaid_inv_line_ids = fields.One2many('unpaid.invoice.line', 'unpaid_invoice_id', string="Plan")
    amount_total = fields.Float(string="Total",compute="get_total")

    @api.depends('unpaid_inv_line_ids.total')
    def get_total(self):
        total = 0
        for line in self.unpaid_inv_line_ids:
            total +=  line.total

        self.amount_total = total

    def reset_sequence(self):
        date = datetime.now()
        obj_sequence = self.env['ir.sequence']
        seq_id = obj_sequence.search([('code','=','unpaid.invoice')])
        if seq_id:
            if date.day == 1:
                seq_id.number_next_actual = 1
                        
    '''def reset_sequence(self):
        obj_sequence = self.env['ir.sequence']
        seq_id = obj_sequence.search([('code','=','unpaid.invoice')])
        seq_lst = []
        if seq_id:
            seq_id.number_next_actual = 1'''
            
    @api.multi
    def export_unpaid_invoice(self):

        filename = 'Unpaid Invoice.xls'
        workbook = xlwt.Workbook()
        style = xlwt.XFStyle()
        tall_style = xlwt.easyxf('font:height 360;')  # 36pt

        font = xlwt.Font()
        font.name = 'Times New Roman'
        font.bold = True
        font.height = 250
        style.font = font
        
        style1 = xlwt.easyxf('font: bold off, color black;\
                     borders: bottom_color black, bottom thin;\
                     pattern: pattern solid, fore_color white;')

        for active_id in self._context['active_ids']:
            
            invoice = self.browse(active_id)
            sheet_name = str(invoice.name).replace("/", "-", 3)
            
            worksheet = workbook.add_sheet(sheet_name)
            worksheet.write_merge(0, 0, 0, 1, str(invoice.name), tall_style)
            worksheet.row(0).height_mismatch = True
            worksheet.row(0).height = 256*2
            
            worksheet.write(3,0,'Collection Date',style)
            worksheet.col(0).width=256*20
            worksheet.col(1).width=256*20
            if invoice.payment_date:
                worksheet.write(3,1,invoice.payment_date)
            
            worksheet.write(3,4,'Created By',style)
            worksheet.col(4).width=256*23
            worksheet.col(5).width=256*23
            if invoice.owner:
                worksheet.write(3,5,invoice.owner.name)
                
            worksheet.write(4,0,'Memo',style)
            if invoice.memo:
                worksheet.write(4,1,invoice.memo)
            
            worksheet.write(7,0,'Customer',style)
            worksheet.write(7,1,'Invoice Date',style)
            worksheet.write(7,2,'Due Date',style)
            worksheet.write(7,3,'Aged',style)
            worksheet.write(7,4,'Reference/Description',style)
            worksheet.write(7,5,'Number',style)
            worksheet.write(7,6,'Sales Person',style)
            worksheet.col(6).width=256*18
            worksheet.write(7,7,'Area',style)
            worksheet.write(7,8,'Region',style)
            worksheet.write(7,9,'Source Document',style)
            worksheet.col(9).width=256*20
            worksheet.write(7,10,'Total',style)
            worksheet.col(10).width=256*20
            
            row = 8
            for line in invoice.unpaid_inv_line_ids:
                if line.partner_id:
                    worksheet.write(row,0,line.partner_id.name)
                if line.date:
                    worksheet.write(row,1,line.date)
                if line.due_date:
                    worksheet.write(row,2,line.due_date)
                if line.aged:
                    worksheet.write(row,3,line.aged)
                if line.reference_id:
                    worksheet.write(row,4,line.reference_id)
                if line.number:
                    worksheet.write(row,5,line.number)
                if line.user_id:
                    worksheet.write(row,6,line.user_id.name)
                if line.area_id:
                    worksheet.write(row,7,line.area_id.name)
                if line.region_id:
                    worksheet.write(row,8,line.region_id.name)
                if line.source_doc:
                    worksheet.write(row,9,line.source_doc)
                if line.total:
                    worksheet.write(row,10,line.total)
                row += 1
            
            worksheet.write(row+3,9,'Total',style)
            worksheet.write(row+3,10,invoice.amount_total,style)
            
            worksheet.write(row+8,0,'Dibuat Oleh :',style)
            worksheet.write(row+8,1,'',style1)
            worksheet.write(row+16,0,'Menyetujui :',style)
            worksheet.write(row+16,1,'',style1)
            
            worksheet.write(row+8,5,'Mengetahui :',style)
            worksheet.write(row+8,6,'',style1)
            worksheet.write(row+16,5,'Diterima Oleh :',style)
            worksheet.write(row+16,6,'',style1)

        fp = StringIO()
        workbook.save(fp)
        export_id = self.env['export.unpaid.invoice'].create({'excel_file': base64.encodestring(fp.getvalue()),'file_name': filename})
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'export.unpaid.invoice',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self._context,
            'target': 'new',
        }

    
class UnpaidInvoiceLine(models.Model):
    _name = 'unpaid.invoice.line'

    unpaid_invoice_id = fields.Many2one('unpaid.invoice', string="Payment")

    partner_id = fields.Many2one('res.partner', 'Customer')
    date = fields.Date('Invoice Date')
    number = fields.Char('Number')
    user_id = fields.Many2one('res.users', string='Sales Person')
    area_id = fields.Many2one("res.partner.area", "Area")
    region_id = fields.Many2one("res.partner.region", "Region")
    due_date = fields.Date('Due Date')
    source_doc = fields.Char('Source Document')
    total = fields.Float('Total')
    aged = fields.Integer('Aged')
    reference_id = fields.Char(string="Reference/Description")
