from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def search_product(self, arg):
        product_id = self.env['product.product'].search([('barcode', '=', str(arg))], limit=1)
        if not product_id:
            product_id = self.env['product.product'].search([('default_code', '=', str(arg))], limit=1)
        product_list = []
        if product_id:
            vals = {}
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['item_no'] = product_id.default_code or ''
            vals['barcode'] = product_id.barcode or ''
            vals['tracking'] = product_id.tracking
            product_list.append(vals)
        else:
            for product_id in self.env['product.product'].search([('name', 'ilike', str(arg))]):
                vals = {}
                vals['product_id'] = product_id.id
                vals['product'] = product_id.name
                vals['item_no'] = product_id.default_code or ''
                vals['barcode'] = product_id.barcode or ''
                vals['tracking'] = product_id.tracking
                product_list.append(vals)
        return product_list

ProductProduct()