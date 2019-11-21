# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import _, api, exceptions, fields, models


class SalesTypeSO(models.Model):
    _name = "sales.type.so"
    
    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    action = fields.Char(string="Action")
    description = fields.Text(string="Description")
    
class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    sales_type_id =  fields.Many2one('sales.type.so', 'Sales Type')


