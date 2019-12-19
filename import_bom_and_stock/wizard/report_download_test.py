from odoo import api, fields, models, _

class inventory_excel_extended(models.TransientModel):

    _name= "excel.extended"

    excel_file = fields.Binary('Dowload report Excel')
    file_name = fields.Char('Excel File', size=64)
