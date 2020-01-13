# -*- coding: utf-8 -*-
# Copyright: Moizasia; Author: Fransiskus Gidi.

from openerp import api, fields, models, _

class CreditLimitWizard(models.TransientModel):
    _name = "credit.limit.wizard"

    @api.multi
    def set_credit_limit_state(self):
        order_id = self.env['sale.order'].browse(self._context.get('active_id'))
        order_id.request_approved()
        return True

    exceeded_amount = fields.Float()
    credit = fields.Float()
