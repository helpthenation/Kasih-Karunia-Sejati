# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_invoice_create_onebyone(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = []

        for order in self:
            inv_data = order._prepare_invoice()
            invoice = inv_obj.create(inv_data)
            invoices.append(invoice)
            for line in order.order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoice.id, line.qty_to_invoice)
                elif line.qty_to_invoice < 0 and final:
                    line.invoice_line_create(invoice.id, line.qty_to_invoice)

        if not invoices:
            raise UserError(_('There is no invoicable line.'))

        for invoice in invoices:
            invoice.compute_taxes()
            if not invoice.invoice_line_ids:
                raise UserError(_('There is no invoicable line.'))
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_total < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view('mail.message_origin_link',
                values={'self': invoice, 'origin': invoice},
                subtype_id=self.env.ref('mail.mt_note').id)
        return [inv.id for inv in invoices]

# class SaleOrderLine(models.Model):
#     _inherit = 'sale.order.line'
#
#     @api.multi
#     def invoice_line_create_onebyone(self, invoice_id, qty):
#         """
#         Create an invoice line. The quantity to invoice can be positive (invoice) or negative
#         (refund).
#
#         :param invoice_id: integer
#         :param qty: float quantity to invoice
#         """
#         pdb.set_trace()
#         precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
#         for line in self:
#             if not float_is_zero(qty, precision_digits=precision):
#                 vals = line._prepare_invoice_line(qty=qty)
#                 vals.update({'invoice_id': invoice_id, 'sale_line_ids': [(6, 0, [line.id])]})
#                 self.env['account.invoice.line'].create(vals)
