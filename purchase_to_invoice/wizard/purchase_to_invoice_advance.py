# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################

import time

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class PurchaseAdvancePaymentInv(models.TransientModel):
    _name = "purchase.advance.payment.inv"

    @api.multi
    def create_invoices(self):
        purchase_orders = self.env['purchase.order'].browse(self._context.get('active_ids', []))
        purchase_orders.action_invoice_create()

        return {'type': 'ir.actions.act_window_close'}
