# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
# from odoo.tools.float_utils import float_compare


class sku(models.Model):
    _name = 'sku.sku'

    name = fields.Char(string="Customer SKU", required=True)
    price = fields.Float(string="Price", required=True)
    customer = fields.Many2one('res.partner', string="Customer", domain=[('customer', '=', True)], required=True)
    sku_product_info_ids = fields.One2many('sku.product.info', 'sku_id', string="Products")

    _sql_constraints = [('customer_uniq', 'unique (customer)', "Customer must be unique")]

    def create_res_partner_sku(self):
        data = {}
        partner_obj = self.env['res.partner.sku']
        if len(self.sku_product_info_ids) == 1:
            data = {
                'price': self.price,
                'sku_id': self.id,
                'partner_id': self.customer.id,
                'product_id': [(6, 0, [self.sku_product_info_ids.mapped('product_id').id])]
            }
        if len(self.sku_product_info_ids) > 1:
            data = {
                'price': self.price,
                'sku_id': self.id,
                'partner_id': self.customer.id,
                'product_id': [(6, 0, self.sku_product_info_ids.mapped('product_id').ids)]
            }
        if data:
            partner_data = partner_obj.search([('sku_id', '=', self.id)])
            if partner_data:
                partner_data.write(data)
            else:
                partner_obj.create(data)

    def create_product_product_sku(self):
        product_obj = self.env['product.product.sku']
        if len(self.sku_product_info_ids) > 0:
            for sku in self.sku_product_info_ids:
                data = {
                    'price': self.price,
                    'sku_id': self.id,
                    'partner_id': self.customer.id,
                    'product_id': sku.product_id.product_tmpl_id.id
                }
                product_data = product_obj.search([('sku_id', '=', self.id), ('product_id', '=', sku.product_id.product_tmpl_id.id)])
                if product_data:
                    product_data.write(data)
                else:
                    product_obj.create(data)

    @api.model
    def create(self, vals):
        res = super(sku, self).create(vals)
        if res:
            res.create_res_partner_sku()
            res.create_product_product_sku()
        return res

    @api.multi
    def write(self, vals):
        res = super(sku, self).write(vals)
        if res:
            self.create_res_partner_sku()
            self.create_product_product_sku()
        return res


class skuProductInfo(models.Model):
    _name = 'sku.product.info'

    sku_id = fields.Many2one('sku.sku', string="Sku Reference")
    int_ref = fields.Char(related="product_id.default_code", string="Internal Reference", required=True, store=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)


class Partner(models.Model):
    _inherit = 'res.partner'

    partner_sku_ids = fields.One2many('res.partner.sku', 'partner_id', string="SKU Info")


class PartnerSku(models.Model):
    _name = 'res.partner.sku'

    partner_id = fields.Many2one('res.partner', string="Partner Ref")
    sku_id = fields.Many2one('sku.sku', string="No.SKU", required=True)
    product_id = fields.Many2many('product.product', string="Product", required=True)
    price = fields.Float(string="Price", required=True)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sku_id = fields.Many2one('sku.sku', string="No.SKU")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if not self.order_id.partner_id:
            raise UserError("Please select the customer First.")
        partner_id = self._context.get('partner_id')
        sku_id = self.env['sku.sku'].search([('customer', '=', partner_id)])
        if any(sku_id):
            self.sku_id = sku_id.id
        return res


# class ProductProduct(models.Model):
#     _inherit = 'product.product'

#     @api.model
#     def name_search(self, name, args=None, operator='ilike', limit=100):
#         args = args or []
#         domain = []
#         if name:
#             domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
#             if operator in expression.NEGATIVE_TERM_OPERATORS:
#                 domain = ['&', '!'] + domain[1:]
#         products = self.search(domain + args, limit=limit)
#         if self._context.get('partner_id'):
#             partner_id = self._context.get('partner_id')
#             sku_obj = self.env['sku.sku'].search([('customer', '=', partner_id)])
#             products_res = sku_obj.sku_product_info_ids.mapped('product_id')
#             if any(products_res):
#                 products = products_res
#             else:
#                 return products_res.name_get()
#         return products.name_get()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_sku_ids = fields.One2many('product.product.sku', 'product_id', string="SKU Info")

#     partner_id = fields.Many2one('res.partner', string="Customer", required=1)
#     sku_id = fields.Many2one('sku.sku', string="Customer SKU", required=1)
#     price = fields.Float(string="Price")


class ProductProductSKU(models.Model):
    _name = 'product.product.sku'

    partner_id = fields.Many2one('res.partner', string="Customer", required=1)
    sku_id = fields.Many2one('sku.sku', string="Customer SKU", required=1)
    price = fields.Float(string="Price")
    product_id = fields.Many2one('product.template', string="Product", required=True)
