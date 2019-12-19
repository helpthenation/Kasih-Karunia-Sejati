# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
import odoo.addons.decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.multi
    @api.depends('invoice_line_ids')
    def _get_analytic_account_name(self):
        for rec in self:
            analytic_account_name = ''
            for line in rec.invoice_line_ids:
                if line.account_analytic_id:
                    analytic_account_name += str(line.account_analytic_id.name) +' | '
            rec.analytic_account_name = analytic_account_name[:-3]
    
    analytic_account_name = fields.Char("Analytic Account", compute="_get_analytic_account_name", store=True)
    

