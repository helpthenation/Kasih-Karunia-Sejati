# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_team_id = fields.Many2one(
        'crm.team',
        string='Sales Team'
    )