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
                self._cr.execute("UPDATE account_invoice set due_status=%s where id=%s", ('paid',invoice.id,))
            if invoice.state == 'draft':
                invoice.update({'due_status_copy': 'Not Due'})
                self._cr.execute("UPDATE account_invoice set due_status=%s where id=%s", ('not_due',invoice.id,))
            if invoice.state == 'open':
                if invoice.date_due:
                    if today_date >= invoice.date_due: 
                        invoice.update({'due_status_copy': 'Due'})
                        self._cr.execute("UPDATE account_invoice set due_status=%s where id=%s", ('due',invoice.id,))
                    else:
                        invoice.update({'due_status_copy': 'Not Due'})
                        self._cr.execute("UPDATE account_invoice set due_status=%s where id=%s", ('not_due',invoice.id,))
                
    
    amount_paid = fields.Float('Amount Paid', readonly=True, compute='_get_amount_paid', store=True)
    due_status = fields.Selection([('due','Due'),('not_due','Not Due'),('paid','Paid')], string='Due Status')
    due_status_copy = fields.Char(string='Due Status COPY', readonly=True, compute='_get_due_status')
    


        
