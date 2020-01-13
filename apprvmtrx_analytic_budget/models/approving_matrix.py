# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class approvingMatrixAnalyticBudget(models.Model):
    _name = 'approving.matrix.analytic.budget'

    name = fields.Char()
    line_ids = fields.One2many('approving.matrix.analytic.budget.line', 'parent_id')
    allow_budget = fields.Boolean(default=False)

class approvingMatrixAnalyticBudgetLine(models.Model):
    _name = 'approving.matrix.analytic.budget.line'

    name = fields.Char()
    parent_id = fields.Many2one('approving.matrix.analytic.budget', ondelete="cascade")

    user_ids = fields.Many2many('res.users')
    min = fields.Float(default=0.0)
    max = fields.Float(default=0.0)
    sequence = fields.Char("Sequence")
    min_approver = fields.Integer('Minimum Approver', default=1)
    approved = fields.Boolean("Approved", copy=False, default=False)
    approved_user_ids = fields.Many2many('res.users', 'approved_user_amount_rel', 'user_ids', 'line_id')
    analytic_budget_id = fields.Many2one('account.analytic.account')

    @api.model
    def check_amount(self, amount):
        if self.min_amount <= amount:
            if self.max_amount == False or self.max_amount == 0 or self.max_amount >= amount:
                return True
        return False
