# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from datetime import datetime


class UnpaidInvoiceWizard(models.TransientModel):
    _name = 'unpaid.invoice.wizard'

    name = fields.Char(string="Name")
    owner = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    payment_date = fields.Date('Collection Date', store=True)
    memo = fields.Char('Memo')
    amount_total = fields.Float(string="Total",compute="get_total")
    unpaid_inv_wiz_line_ids = fields.One2many('unpaid.invoice.wiz.line', 'unpaid_inv_id', string="Plan")

    @api.depends('unpaid_inv_wiz_line_ids.total')
    def get_total(self):
        total = 0
        for line in self.unpaid_inv_wiz_line_ids:
            total +=  line.total

        self.amount_total = total

    @api.model
    def default_get(self, vals):
        res = super(UnpaidInvoiceWizard, self).default_get(vals)
        inv_paid = self.env['account.invoice'].search([('state','in',['paid']),('id','in',self._context.get('active_ids'))])
        if inv_paid:
            raise Warning('Paid Invoice cannot be processed.')

        else:
            unpaid_inv_line = self.env['account.invoice'].browse(self._context.get('active_ids'))
            unpaid_inv = []
            for bill in unpaid_inv_line:
                area_id = False
                if bill.partner_id.area_id:
                    area_id = bill.partner_id.area_id.id
                
                region_id = False
                if bill.partner_id.region_id:
                    region_id = bill.partner_id.region_id.id
                    
                dict = (0,0, {
                    'partner_id': bill.partner_id.id,
                    'date': bill.date_invoice,
                    # 'aged': bill.aged,
                    'number': bill.number,
                    'user_id': bill.user_id.id,
                    'area_id': area_id,
                    'region_id': region_id,
                    'due_date': bill.date_due,
                    'source_doc': bill.origin,
                    'reference_id': bill.name,
                    'total': bill.amount_total,
                    })
                unpaid_inv.append(dict)
            res.update({'unpaid_inv_wiz_line_ids' :unpaid_inv})
        return res

    @api.onchange('payment_date')
    def onchange_payment_date(self):
        """Onchange correction date Method."""
        if self.payment_date:
            for line in self.unpaid_inv_wiz_line_ids:
                aged_int = datetime.strptime(self.payment_date, "%Y-%m-%d").date() - datetime.strptime(line.due_date, "%Y-%m-%d").date()
                aged_days = aged_int.days
                print"======================",aged_days,line
                line.update({'aged' :aged_days})

    @api.multi
    def create_unpaid_inv_line(self):
        unpaid_inv_model = self.env['unpaid.invoice']
        order_list = []
        if self.payment_date:
            for line in self.unpaid_inv_wiz_line_ids:
                aged_int = datetime.strptime(self.payment_date, "%Y-%m-%d").date() - datetime.strptime(line.due_date, "%Y-%m-%d").date()
                aged_days = aged_int.days
                print"======================",aged_days,line

        for order in self:
            for line in order.unpaid_inv_wiz_line_ids:
                area_id = False
                if line.area_id:
                    area_id = line.area_id.id
                region_id = False
                if line.region_id:
                    region_id = line.region_id.id
                order_list.append((0,0,{
                    'partner_id':line.partner_id.id,
                    'date':line.date,
                    'aged': aged_days,
                    'number':line.number,
                    'user_id':line.user_id.id,
                    'area_id':area_id,
                    'region_id':region_id,
                    'due_date':line.due_date,
                    'source_doc':line.source_doc,
                    'reference_id': line.reference_id,
                    'total':line.total,
                    }))

            unpaid_inv = unpaid_inv_model.create({
                'owner':order.owner.id,
                'payment_date':order.payment_date,
                'memo':order.memo,
                'unpaid_inv_line_ids':order_list
                })
            
            if unpaid_inv:
                self.unpaid_inv_id = unpaid_inv.id

                res = {
                        'name':'Payment Plan',
                        'view_type':'form',
                        'view_mode':'form',
                        'res_model':'unpaid.invoice',
                        'type':'ir.actions.act_window',
                        'target':'current',
                        'context':{},
                    }

                if self.unpaid_inv_id:
                    res['res_id'] = unpaid_inv.id
                return res
                              

class UnpaidInvoiceWizLine(models.TransientModel):
    _name = 'unpaid.invoice.wiz.line'

    unpaid_inv_id = fields.Many2one('unpaid.invoice.wizard', string="Payment")

    partner_id = fields.Many2one('res.partner', 'Customer')
    date = fields.Date('Invoice Date')
    number = fields.Char('Number')
    user_id = fields.Many2one('res.users', string='Sales Person')
    area_id = fields.Many2one("res.partner.area", "Area")
    region_id = fields.Many2one("res.partner.region", "Region")
    source_doc = fields.Char('Source Document')
    due_date = fields.Date('Due Date')
    source_doc = fields.Char('Source Document')
    total = fields.Float('Total')
    aged = fields.Integer('Aged')
    reference_id = fields.Char(string="Reference/Description")

