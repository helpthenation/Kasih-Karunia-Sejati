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
    sku_id = fields.Many2one('sku.sku', string="Customer SKU", required=True)
    product_id = fields.Many2many('product.product', string="Product", required=True)
    price = fields.Float(string="Price", required=True)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sku_id = fields.Many2one('sku.sku', string="Customer SKU")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        super(SaleOrderLine, self).product_id_change()
        if not self.order_id.partner_id:
            raise UserError("Please select the customer First.")
        domain = {}
        if self.product_id:
            data = self.env['res.partner.sku'].search([('product_id', '=', self.product_id.id), ('partner_id', '=', self.order_id.partner_id.id)])
            sku_list = [d.sku_id.id for d in data]
            if not sku_list:
                domain.update({'domain': {'sku_id': [('id', 'in', [])]}})
            domain.update({'domain': {'sku_id': [('id', 'in', sku_list)]}})
        else:
            domain.update({'domain': {'sku_id': [('id', 'in', [])]}})
        return domain


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get('res_model') == 'sale.order':
            partner_id = self._context.get('partner_id')
            sku_ids = self.env['sku.sku'].search([('customer', '=', partner_id)])
            if sku_ids:
                line_ids = []
                for rec in sku_ids:
                    for line in rec.sku_product_info_ids:
                        if line.product_id.id not in line_ids:
                            line_ids.append(str(line.product_id.id))
                print "Line_idddddddddddddd", line_ids
                child_str = ", ".join(tuple(line_ids))
                product_ids = []
                if child_str:
                    self._cr.execute("""
                        SELECT
                            id
                        FROM
                            product_product
                        WHERE
                            id in (%s)
                    """ % (child_str))
                    res = self._cr.dictfetchall()
                    if res:
                        product_ids = [i['id'] for i in res]
                        args += [('id', 'in', product_ids)]
                else:
                    args = [('id', 'in', product_ids)]
        print "argsss", args
        return super(ProductProduct, self)._search(args=args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_sku_ids = fields.One2many('product.product.sku', 'product_id', string="SKU Info")


class ProductProductSKU(models.Model):
    _name = 'product.product.sku'

    partner_id = fields.Many2one('res.partner', string="Customer", required=1)
    sku_id = fields.Many2one('sku.sku', string="Customer SKU", required=1)
    price = fields.Float(string="Price")
    product_id = fields.Many2one('product.template', string="Product", required=True)
