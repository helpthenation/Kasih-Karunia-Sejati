from odoo import api, fields, models, _



class adjustment_type(models.Model):
    _name = 'adjustment.type'

    name = fields.Text(string="Name")
    code =fields.Text("Code")
    description = fields.Text("Description")
    action = fields.Text("Action")
    adjustment_type = fields.Char("Adjustment type")


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    adjustment_type = fields.Many2one(comodel_name="adjustment.type", string="Adjustment type")