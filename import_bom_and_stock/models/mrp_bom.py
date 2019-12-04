# -*- coding: utf-8 -*-

from odoo import models, fields, api 

class ProductTemplate(models.Model):

    _inherit = "product.template"

    @api.multi
    def name_get(self):
        result = []
        if self._context.get('from_bom'):
            return [(template.id, '%s' % (template.name))
                for template in self]
        result = super(models.Model, self).name_get()
        return result

class ProductProduct(models.Model):

    _inherit = "product.product"

    @api.multi
    def name_get(self):
        result = []
        if self._context.get('from_bom'):
            return [(obj.id, '%s' % (obj.name))
                for obj in self]
        result = super(models.Model, self).name_get()
        return result

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        res = super(MrpBom, self).onchange_product_tmpl_id()
        if self.product_tmpl_id:
            product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)], limit=1)
            if product_id:
                self.product_id = product_id.id
        return res
