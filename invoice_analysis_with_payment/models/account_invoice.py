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
                
    
    amount_paid = fields.Float('Amount Paid', readonly=True, compute='_get_amount_paid', store=True)
    


        
