# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

class UnpaidInvoice(models.Model):
    _name = 'unpaid.invoice'

    name = fields.Char('Name')
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('unpaid.invoice') or '/'
        return super(UnpaidInvoice, self).create(vals)

    owner = fields.Many2one('res.users', string='Requested By')
    payment_date = fields.Date('Payment Date')
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
