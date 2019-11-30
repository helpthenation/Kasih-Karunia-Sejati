# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class payment_plan_wizard(models.TransientModel):
    _name = 'payment.plan.wizard'

    name = fields.Char(string="Name")
    owner = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    payment_date = fields.Date('Payment Date')
    memo = fields.Char('Memo')
    amount_total = fields.Float(string="Total",compute="get_total")

    payment_line_ids = fields.One2many('payment.plan.line', 'payment_id', string="Plan")

    @api.depends('payment_line_ids.total')
    def get_total(self):
        total = 0
        for line in self.payment_line_ids:
            total +=  line.total

        self.amount_total = total

    @api.model
    def default_get(self, vals):
        res = super(payment_plan_wizard, self).default_get(vals)
        payment_paid = self.env['account.invoice'].search([('state','in',['paid']),('id','in',self._context.get('active_ids'))])
        if payment_paid:
            raise Warning('Paid bill cannot be processed.')

        else:
            payment_line = self.env['account.invoice'].browse(self._context.get('active_ids'))
            payment = []
            for bill in payment_line:
                dict = (0,0, {
                    'partner_id': bill.partner_id.id,
                    'date': bill.date_invoice,
                    'number': bill.number,
                    'reference': bill.reference,
                    'due_date': bill.date_due,
                    'source_doc': bill.origin,
                    'total': bill.amount_total,
                    })
                payment.append(dict)
            res.update({'payment_line_ids' :payment})
        return res

    @api.multi
    def create_payment_line(self):
        payment_model = self.env['payment.plan']
        order_list = []
        for order in self:
            for line in order.payment_line_ids:
                order_list.append((0,0,{
                    'partner_id':line.partner_id.id,
                    'date':line.date,
                    'number':line.number,
                    'reference':line.reference,
                    'due_date':line.due_date,
                    'source_doc':line.source_doc,
                    'total':line.total,
                    }))

            payment = payment_model.create({
                'owner':order.owner.id,
                'payment_date':order.payment_date,
                'memo':order.memo,
                'plan_line_ids':order_list
                })
            
            if payment:
                self.payment_plan_id = payment.id

                res = {
                        'name':'Payment Plan',
                        'view_type':'form',
                        'view_mode':'form',
                        'res_model':'payment.plan',
                        'type':'ir.actions.act_window',
                        'target':'current',
                        'context':{},
                    }

                if self.payment_plan_id:
                    res['res_id'] = payment.id
                return res
                              

class payment_plan_line(models.TransientModel):
    _name = 'payment.plan.line'

    payment_id = fields.Many2one('payment.plan.wizard', string="Payment")

    partner_id = fields.Many2one('res.partner', 'Vendor')
    date = fields.Date('Bill Date')
    number = fields.Char('Number')
    reference = fields.Char('Vendor Reference')
    due_date = fields.Date('Due Date')
    source_doc = fields.Char('Source Document')
    total = fields.Float('Total')