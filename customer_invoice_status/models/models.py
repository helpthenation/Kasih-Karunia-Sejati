# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Partner'

    invoice_status = fields.Selection([('over_due', 'Over Due'),
                                       ('no_over_due', 'No Over Due')], compute='compute_invoice_status')

    current_date = fields.Date(default=datetime.today(), string='Date')


    @api.depends('invoice_status')
    def compute_invoice_status(self):
        for partner in self:    
            invoice_id = partner.env['account.invoice'].search([('partner_id', '=', partner.name)])
            for rec in invoice_id:
                if rec.date_due > partner.current_date and rec.state in 'paid':
                    partner.invoice_status = 'no_over_due'
                else:
                    partner.invoice_status = 'over_due'