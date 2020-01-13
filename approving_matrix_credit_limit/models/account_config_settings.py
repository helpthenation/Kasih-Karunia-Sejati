# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    block_over_limit = fields.Boolean('Block Transaction If Over Credit Limit')
    allow_over_limit = fields.Boolean('Allow Over Credit Approval')

    @api.multi
    def set_block_over_limit(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'block_over_limit', self.block_over_limit)

    @api.multi
    def set_allow_over_limit(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'allow_over_limit', self.allow_over_limit)