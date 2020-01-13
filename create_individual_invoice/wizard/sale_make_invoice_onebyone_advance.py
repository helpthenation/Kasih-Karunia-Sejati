# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################

import time

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class SaleAdvancePaymentOnebyoneInv(models.TransientModel):
    _name = "sale.advance.payment.onebyone.inv"

    @api.model
    def _count(self):
        return len(self._context.get('active_ids', []))

    @api.model
    def _get_advance_payment_method(self):
        if self._count() == 1:
            sale_obj = self.env['sale.order']
            order = sale_obj.browse(self._context.get('active_ids'))[0]
            if all([line.product_id.invoice_policy == 'order' for line in order.order_line]) or order.invoice_count:
                return 'all'
        return 'delivered'

    advance_payment_method = fields.Selection([
        ('delivered', 'Invoiceable lines'),
        ('all', 'Invoiceable lines (deduct down payments)'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
        ], string='What do you want to invoice?', default=_get_advance_payment_method, required=True)

    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            sale_orders.action_invoice_create_onebyone()
        elif self.advance_payment_method == 'all':
            sale_orders.action_invoice_create_onebyone(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                else:
                    tax_ids = taxes.ids
                context = {'lang': order.partner_id.lang}
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'tax_id': [(6, 0, tax_ids)],
                })
                del context
                self._create_invoice(order, so_line, amount)
        return {'type': 'ir.actions.act_window_close'}
