# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    aged = fields.Integer('Aged')

    @api.multi
    @api.onchange('date_due')
    def onchange_date_due(self):
        current_date = datetime.today().date()
        if self.date_due:
            delta = datetime.strptime(self.date_due, "%Y-%m-%d").date() - current_date
            self.aged = int(delta.days)
