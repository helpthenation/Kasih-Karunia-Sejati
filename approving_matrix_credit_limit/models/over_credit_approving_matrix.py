# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreditApprovingMatrix(models.Model):
    _name = 'credit.approving.matrix'

    name = fields.Text('Name')
    branch_id = fields.Many2one('res.branch', 'Branch')
    credit_approving_matrix_ids = fields.One2many('credit.approving.lines', 'credit_approving_id', 'Credit Approving Lines')


class CreditApprovingLines(models.Model):
    _name = 'credit.approving.lines'

    credit_approving_id = fields.Many2one('credit.approving.matrix', 'Credit Approving Matrix')
    sequence = fields.Char('Sequence')
    user_id = fields.Many2many('res.users', string='User')
    min_approver = fields.Integer('Minimum Approver', default=1)
    min_amount = fields.Float('Minimum Amount ')
    max_amount = fields.Float('Maximum Amount')
    approved_user_ids   = fields.Many2many('res.users','approved_user_matrix_rel','user_id','line_id')
    credit_approving_sale_id = fields.Many2one('sale.order', string='Sale Id')
    approved = fields.Boolean("Approved", copy=False, default=False)