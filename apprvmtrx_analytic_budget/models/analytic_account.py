# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.depends('product_budget_lines.planned_amount')
    def _compute_price_unit_all(self):
        total = 0
        for rec in self:
            for line in rec.product_budget_lines:
                total = total + line.planned_amount
            rec.budget_total = total

    @api.depends('budget_total', 'approving_matrix_id', 'product_budget_lines.planned_amount')
    def _get_approval_matrix_line(self):
        for rec in self:
            rec.approving_matrix_line_ids = False
            approval_matrix_lines = []
            approval_matrix_lines_dic = {}
            if rec.approving_matrix_id and not rec.product_budget_lines:
                for line in rec.approving_matrix_id.line_ids:
                    if line.sequence not in approval_matrix_lines_dic:
                        approval_matrix_lines_dic[line.sequence] = [[0, 0, {
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'name': line.name,
                            'min': line.min,
                            'max': line.max,
                            'approved': False,
                            'sequence': line.sequence,
                            'min_approver': line.min_approver
                        }
                                                                     ]]
                    else:
                        temp = approval_matrix_lines_dic[line.sequence]
                        temp.append([0, 0, {
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'name': line.name,
                            'min': line.min,
                            'max': line.max,
                            'approved': False,
                            'sequence': line.sequence,
                            'min_approver': line.min_approver
                        }
                                     ])
                        approval_matrix_lines_dic[line.sequence] = temp
            elif rec.approving_matrix_id and rec.product_budget_lines:

                approval_lines = rec.approving_matrix_id.line_ids.filtered(lambda r: r.min <= rec.budget_total and r.max >= rec.budget_total)
                for line in approval_lines:
                    if line.sequence not in approval_matrix_lines_dic:
                        approval_matrix_lines_dic[line.sequence] = [[0, 0, {
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'name': line.name,
                            'min': line.min,
                            'max': line.max,
                            'approved': False,
                            'sequence': line.sequence,
                            'min_approver': line.min_approver
                        }
                                                                     ]]
                    else:
                        temp = approval_matrix_lines_dic[line.sequence]
                        temp.append([0, 0, {
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'name': line.name,
                            'min': line.min,
                            'max': line.max,
                            'approved': False,
                            'sequence': line.sequence,
                            'min_approver': line.min_approver
                        }
                                     ])
                        approval_matrix_lines_dic[line.sequence] = temp

            approval_matrix_lines = []
            if approval_matrix_lines_dic:
                for key in sorted(approval_matrix_lines_dic):
                    print "%s: %s" % (key, approval_matrix_lines_dic[key])
                    temp_list = approval_matrix_lines_dic[key]
                    if len(temp_list) > 1:
                        for ele in temp_list:
                            approval_matrix_lines.append(ele)
                    else:
                        approval_matrix_lines.append(temp_list[0])

            rec.approving_matrix_line_ids = approval_matrix_lines


    budget_total = fields.Monetary(compute='_compute_price_unit_all', store=True, copy=False)
    approving_matrix_id = fields.Many2one('approving.matrix.analytic.budget', copy=False, ondelete="restrict")
    approving_matrix_line_ids = fields.One2many('approving.matrix.analytic.budget.line', 'analytic_budget_id',
                  compute="_get_approval_matrix_line", store=True, copy=False)
    is_multiline_approval = fields.Boolean(default=False, copy=False, compute='check_next_approver')
    is_button_rejected = fields.Boolean(default=False, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Budget Waiting for Approval'),
        ('approved', 'Budget Approved'),
        ('reject', 'Rejected')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    @api.multi
    def check_next_approver(self):
        self.is_multiline_approval = True
        if self.approving_matrix_line_ids:
            lines_amount = self.approving_matrix_line_ids.filtered(lambda r: r.approved == False)
            sorted_seq_data = lines_amount.sorted('sequence')
            next_seq = 0
            if sorted_seq_data:
                next_seq = sorted_seq_data[0].sequence
            approved_line_amount = lines_amount.filtered(lambda r: r.sequence == next_seq)
            if approved_line_amount and any(line.min_approver >= 2 for line in approved_line_amount):
                if self.env.user.id in approved_line_amount.mapped('user_ids.id') and any(
                        self.env.user.id not in line.approved_user_ids.ids for line in approved_line_amount):
                    self.is_multiline_approval = False
            elif self.env.user.id in approved_line_amount.mapped('user_ids.id'):
                self.is_multiline_approval = False

    @api.multi
    def request_approve(self):
        lines_amount = self.approving_matrix_line_ids.filtered(lambda r: r.approved == False)
        sorted_seq_data = lines_amount.sorted('sequence')
        next_seq = 0
        if sorted_seq_data:
            next_seq = sorted_seq_data[0].sequence

        approved_line_amount = lines_amount.filtered(lambda r: r.sequence == next_seq)
        for line in approved_line_amount:
            if line.user_ids and len(line.user_ids) > 0:
                user_ids = line.mapped('user_ids')
                """ create notification in discussion panel """
                if user_ids:
                    self.send_mail_approval_process(user_ids)

        if lines_amount:
            self.state = 'to_approve'
        else:
            self.state = 'approved'

    @api.multi
    def approving(self):
        approved_line_amount = self.approving_matrix_line_ids.filtered(lambda r: r.approved == False)
        # print("***************", approved_pr_line_amount.sorted('sequence'))
        sorted_seq_data = approved_line_amount.sorted('sequence')
        next_seq = 0
        if sorted_seq_data:
            next_seq = sorted_seq_data[0].sequence

        approved_line_amount = approved_line_amount.filtered(lambda r: r.sequence == next_seq)
        # print("====>>>>>>>>>>>", approved_pr_line_amount)
        approve_flg = False
        if approved_line_amount:
            for line in approved_line_amount:
                # print("==========>>>>>>>>", line.user_id)
                if line.user_ids and len(line.user_ids) > 0:
                    user_ids = line.mapped('user_ids').ids
                    if self._uid in user_ids and (
                            line.min_approver == (len(line.approved_user_ids.ids) + 1) or line.min_approver <= 1):
                        approve_flg = True
                        line.write({'approved': True})
                        return self.request_approve()
                    else:
                        line.approved_user_ids += self.env.user

    @api.multi
    def send_mail_approval_process(self, receiver):
        view = 'Budgeting'
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        link = base_url + '/web#id=%s&view_type=form&model=account.analytic.account' % self.id

        receivers = ''
        for partner in receiver:
            receivers += partner.name + ','

        body_dynamic_html = '<p>Dear %s </p>' % receivers
        body_dynamic_html += '<p> Request you to approve: %s </p>' % self.name
        body_dynamic_html += '<p> Requestor: %s </p>' % self.create_uid.name

        body_dynamic_html += '<div style = "margin: 16px;">\
                                    <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                     color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                     margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                     cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                     border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
            link, view)

        thread_pool = self.env['mail.message'].sudo().create({
            'subject': 'You have a Analytic Budget need approval',
            'body': body_dynamic_html,
            'model': 'account.analytic.account',
            'partner_ids': [(6, 0, receiver.mapped('partner_id').ids)],
            'needaction_partner_ids': [(6, 0, receiver.mapped('partner_id').ids)],
        })

        thread_pool.needaction_partner_ids = [(6, 0, receiver.mapped('partner_id').ids)]

    @api.multi
    def rejected(self):
        self.state = 'reject'
        for record in self:
            approving_matrix_line = len(record.approving_matrix_line_ids)
            if approving_matrix_line > 1:
                self.is_button_rejected = True
        return True
