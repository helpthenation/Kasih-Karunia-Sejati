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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SaleOrder, self).onchange_partner_id()
        if len(self.partner_id.partner_sku_ids) > 0:
            product_list = [pro for pro in self.partner_id.partner_sku_ids.product_id]
            data_list = []
            for pro_sku in product_list:
                name = pro_sku.name_get()[0][1]
                if pro_sku.description_sale:
                    name += '\n' + pro_sku.description_sale
                data_list.append({
                    'product_id': pro_sku.id,
                    'sku_id': self.partner_id.partner_sku_ids.sku_id.id,
                    'name': name,
                    'product_uom': pro_sku.uom_id,
                    'product_uom_qty':  1.0
                    })
            self.order_line = [(0, 0, d) for d in data_list]
        # else:
            # self.order_line = []
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sku_id = fields.Many2one('sku.sku', string="Customer SKU")

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

    # @api.model
    # def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
    #     categ_id = self.env.context.get('id', False)
    #     print "ffffffff", self, categ_id
    #     child_id = self.env['sale.order'].browse(categ_id)
    #     print "qqqqqqqqqqqq", child_id
    #     customer_id = self.order_id.partner_id
    #     print ('aaaaaaaaa', customer_id)
    #     if customer_id:
    #         # sku_id = self.env['sku.sku'].serach([('customer', '=', customer_id.id)])
    #         # if sku_id:
    #         self._cr.execute("""
    #             SELECT
    #                 product_id
    #             FROM
    #                 sku_product_info
    #             WHERE
    #                 sku_id in ( SELECT id FROM sku_sku where customer = (%s)
    #                             )
    #         """ % (customer_id.id))
    #         res = self._cr.dictfetchall()
    #         print ("ssssssssssss", res)
    #         product_id = []
    #         if res:
    #             product_id = [i['product_id'] for i in res]
    #         args += [('id', 'in', product_id)]
    #     return super(SaleOrderLine, self)._search(args=args, offset=offset,
    #                                               limit=limit, order=order,
    #                                               count=count, access_rights_uid=access_rights_uid)


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
