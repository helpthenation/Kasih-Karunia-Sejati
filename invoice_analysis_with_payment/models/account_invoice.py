from __future__ import division
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import ustr
from datetime import datetime,timedelta

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.depends('amount_total','residual')
    def _get_amount_paid(self):
        for invoice in self:
            amount_paid = invoice.amount_total - invoice.residual
            invoice.update({'amount_paid': amount_paid})
            
    @api.depends('date_due','state')
    def _get_due_status(self):
        for invoice in self:
            today_date = fields.Date.context_today(self)
            if invoice.state == 'paid':
                invoice.update({'due_status_copy': 'Paid'})
                invoice.due_status = 'paid'
            else:
                if invoice.date_due and invoice.state == 'open':
                    if today_date >= invoice.date_due: 
                        invoice.update({'due_status_copy': 'Due'})
                        invoice.due_status = 'due'
                    else:
                        invoice.update({'due_status_copy': 'Not Due'})
                        invoice.due_status = 'not_due'
                else:
                    invoice.update({'due_status_copy': 'Not Due'})
                    invoice.due_status = 'not_due'           
                
    
    amount_paid = fields.Float('Amount Paid', readonly=True, compute='_get_amount_paid', store=True)
    due_status = fields.Selection([('due','Due'),('not_due','Not Due'),('paid','Paid')], string='Due Status', readonly=True)
    due_status_copy = fields.Char(string='Due Status COPY', readonly=True,compute='_get_due_status')
    


        
