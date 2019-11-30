from odoo import api, fields, models, _



class adjustment_type(models.Model):
    _name = 'adjustment.type'

    name = fields.Text(string="Name")
    code =fields.Text("Code")
    description = fields.Text("Description")
    action = fields.Text("Action")
