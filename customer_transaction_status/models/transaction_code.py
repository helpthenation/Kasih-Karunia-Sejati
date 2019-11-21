# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Partner'

    code = fields.Selection([('0', '0'),
                             ('1', '1'),
                             ('2', '2'),
                             ('3', '3')], compute="compute_transaction_status")
    transaction_status = fields.Selection([('normal', 'Normal'),
                                           ('over_limit', 'Over Limit'),
                                           ('over_due', 'Over Due'),
                                           ('over_limit_over_due', 'Over Limit & Over Due')],
                                            string="Transaction Status", compute="compute_transaction_status")

    current_date = fields.Date(default=datetime.today(), string='Date')

    @api.depends('credit_limit')
    def compute_transaction_status(self):
        for partner in self:
            invoice_id = partner.env['account.invoice'].search([('partner_id', '=', partner.id), ('state', '!=', 'paid')])
            if partner.credit_limit:
                if partner.credit_limit <= partner.available_credit:
                    partner.code = '0'
                    partner.transaction_status = 'normal'

                elif partner.credit_limit > partner.available_credit:
                    partner.code = '1'
                    partner.transaction_status = 'over_limit'

                for rec in invoice_id:
                    if partner.invoice_status == 'over_due':
                        partner.code = '2'
                        partner.transaction_status = 'over_due'
                        
                    elif partner.credit_limit > partner.available_credit and partner.credit_limit > invoice_id.amount_total:
                        partner.code = '3'
                        partner.transaction_status = 'over_limit_over_due'