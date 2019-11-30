# -*- coding: utf-8 -*-

from odoo import models, fields, api

class payment_plan(models.Model):
    _name = 'payment.plan'

    name = fields.Char('Name')
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('payment.plan') or '/'
        return super(payment_plan, self).create(vals)

    owner = fields.Many2one('res.users', string='Requested By')
    payment_date = fields.Date('Payment Date')
    memo = fields.Char('Memo')

    plan_line_ids = fields.One2many('payment.line', 'payment_id', string="Plan")
    amount_total = fields.Float(string="Total",compute="get_total")


    @api.depends('plan_line_ids.total')
    def get_total(self):
        total = 0
        for line in self.plan_line_ids:
            total +=  line.total

        self.amount_total = total

    def reset_sequence(self):
        obj_sequence = self.env['ir.sequence']
        seq_id = obj_sequence.search([('code','=','payment.plan')])
        seq_lst = []
        if seq_id:
            seq_id.number_next_actual = 1

    
class payment_line(models.Model):
    _name = 'payment.line'

    payment_id = fields.Many2one('payment.plan', string="Payment")

    partner_id = fields.Many2one('res.partner', 'Vendor')
    date = fields.Date('Bill Date')
    number = fields.Char('Number')
    reference = fields.Char('Vendor Reference')
    due_date = fields.Date('Due Date')
    source_doc = fields.Char('Source Document')
    total = fields.Float('Total')