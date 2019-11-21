# -*- coding: utf-8 -*-
# Copyright 2017 Omar Castiñeira, Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResPartnerRegion(models.Model):
    '''New dimension of customer's categorization'''

    _name = "res.partner.region"
    _order = "name asc"

    name = fields.Char("Name", required=True)
    code = fields.Char('Code', size=15)
