# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        approver_in_list = False
        ir_values_obj = self.env['ir.values']
        block_over_limit = ir_values_obj.get_default('account.config.settings', 'block_over_limit')
        allow_over_limit = ir_values_obj.get_default('account.config.settings', 'allow_over_limit')
        approving_matrix = self.credit_approving_matrix_id
        for approve_lines in approving_matrix.credit_approving_matrix_ids:
            if self._uid in approve_lines.user_id.ids:
                approver_in_list = True
        if block_over_limit:
            invoice_ids = self.env['account.invoice'].search([('partner_id','=',self.partner_id.id), ('state','=','open')])
            total_inv_price = 0
            total_price = 0
            for rec in invoice_ids:
                total_inv_price += rec.amount_total
            total_price = total_inv_price + self.amount_total 
            limit_remain = self.partner_id.credit_limit - total_inv_price
            if total_price > self.partner_id.credit_limit:
                imd = self.env['ir.model.data']
                exceeded_amount = self.amount_total - limit_remain
                vals_wiz={
                    'exceeded_amount': exceeded_amount,
                    'credit': limit_remain,
                    }
                wiz_id = self.env['credit.limit.wizard'].create(vals_wiz)
                action = self.env['ir.model.data'].xmlid_to_object('approving_matrix_credit_limit.action_credit_limit_wizard')
                form_view_id = self.env['ir.model.data'].xmlid_to_res_id('approving_matrix_credit_limit.view_credit_limit_wizard_form')
                return  {
                        'name': action.name,
                        'help': action.help,
                        'type': action.type,
                        'views': [(form_view_id, 'form')],
                        'view_id': form_view_id,
                        'target': action.target,
                        'context': action.context,
                        'res_model': action.res_model,
                        'res_id': wiz_id.id,
                        }
        return res

    
    @api.depends('credit_approving_matrix_id','order_line.price_unit')
    def _get_approval_matrix_line(self):
        for rec in self:
            rec.approving_matrix_line_ids = False
            approval_matrix_lines = []
            approval_matrix_lines_dic = {}
            if rec.credit_approving_matrix_id and rec.order_line:
                for line in rec.credit_approving_matrix_id.credit_approving_matrix_ids:
                    if line.sequence not in approval_matrix_lines_dic:
                        approval_matrix_lines_dic[line.sequence] = [[0, 0, {
                            'user_id': [(6, 0, line.user_id.ids)],
                            'min_amount': line.min_amount,
                            'max_amount': line.max_amount,
                            'approved': False,
                            'sequence': line.sequence,
                            'min_approver': line.min_approver
                        }]]
                    else:
                        temp = approval_matrix_lines_dic[line.sequence]
                        temp.append([0, 0, {
                            'user_id': [(6, 0, line.user_id.ids)],
                            'min_amount': line.min_amount,
                            'max_amount': line.max_amount,
                            'approved': False,
                            'sequence': line.sequence,
                            'min_approver': line.min_approver
                        }])
                        approval_matrix_lines_dic[line.sequence] = temp

            approval_matrix_lines = []
            if approval_matrix_lines_dic:
                for key in sorted(approval_matrix_lines_dic):
                    temp_list = approval_matrix_lines_dic[key]
                    if len(temp_list) > 1:
                        for ele in temp_list:
                            approval_matrix_lines.append(ele)
                    else:
                        approval_matrix_lines.append(temp_list[0])

            rec.credit_approving_matrix_line_ids = approval_matrix_lines

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })
            ir_values_obj = self.env['ir.values']
            allow_credit = ir_values_obj.get_default('account.config.settings', 'allow_over_limit')
            if allow_credit:
                if order.partner_id.credit_limit:
                    credit_apprv_matrix_ids = self.env['credit.approving.matrix'].search([])
                    for credit in credit_apprv_matrix_ids:
                        for line in credit.credit_approving_matrix_ids:
                            if order.amount_total > line.min_amount and order.amount_total < line.max_amount:
                                order.update({
                                    'credit_approving_matrix_id' : credit.id
                                    })
                            else:
                                order.update({
                                    'credit_approving_matrix_id' : False
                                    })




    credit_approving_matrix_id = fields.Many2one('credit.approving.matrix', 'Approving Matrix',copy=False)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('to_approved', 'To be Approve'), 
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    credit_approving_matrix_line_ids = fields.One2many('credit.approving.lines', 'credit_approving_sale_id', 'Credit Approving Lines',compute="_get_approval_matrix_line", store=True, copy=False)
    confirm_sale_boolean = fields.Boolean(string="confirm_sale_boolean")

    price_total = fields.Monetary(compute='_compute_price_unit_all', string='Total price_unit', store=True, copy=False)
    is_multiline_approval = fields.Boolean(string="Approve", default=False, copy=False, compute='check_next_approver')
    is_button_rejected = fields.Boolean(string="Reject", default=False, copy=False)
    credit_exceed =  fields.Boolean(string="Check Credit", default=False, copy=False, compute='check_credit_exceed')
    approver_in_list = fields.Boolean(string="Can approve")
    
    
    
    @api.multi
    def send_mail_quote_approval_process(self, receiver):
        view = 'RFQ'
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        link = base_url + '/web#id=%s&view_type=form&model=sale.order' % self.id
        receivers = ''
        for partner in receiver:
            receivers += partner.name + ','
        body_dynamic_html =  '<p>Dear %s </p>' % receivers
        body_dynamic_html += '<p> Request you to approve RFQ: %s </p>' % self.name
        body_dynamic_html += '<p> Requestor: %s </p>' % self.create_uid.name
        body_dynamic_html += '<div style = "margin: 16px;">\
                                    <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                     color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                     margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                     cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                     border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
            link, view)
        thread_pool = self.env['mail.message'].sudo().create({
            'subject': 'You have a RFQ need approval',
            'body': body_dynamic_html,
            'model': 'sale.order',
            'partner_ids': [(6, 0, receiver.mapped('partner_id').ids)],
            'res_id': self.id,
            'needaction_partner_ids': [(6, 0, receiver.mapped('partner_id').ids)],
        })
        thread_pool.needaction_partner_ids = [(6, 0, receiver.mapped('partner_id').ids)]


    @api.multi
    def request_quote_approve(self):
        lines_amount = self.credit_approving_matrix_line_ids.filtered(lambda r: r.approved == False)
        sorted_seq_data = lines_amount.sorted('sequence')
        next_seq = 0
        if sorted_seq_data:
            next_seq = sorted_seq_data[0].sequence
        approved_qr_line_amount = lines_amount.filtered(lambda r: r.sequence == next_seq)
        for line in approved_qr_line_amount:
            if line.user_id and len(line.user_id) > 0:
                user_ids = line.mapped('user_id')
                if user_ids:
                    self.send_mail_quote_approval_process(user_ids)
        if lines_amount:
            self.state = 'to_approved'
        else:
#             self.state = 'approved'
            self.state = 'sale'

    @api.multi
    def quote_approved(self):
        approved_qr_line_amount = self.credit_approving_matrix_line_ids.filtered(lambda r: r.approved == False)
        #         approver_seq_list = []
        #         for line in approved_qr_line_amount:
        #             approver_seq_list.append(line.sequence)
        sorted_seq_data = approved_qr_line_amount.sorted('sequence')
        
        next_seq = 0
        if sorted_seq_data:
            next_seq = sorted_seq_data[0].sequence

        approved_qr_line_amount = approved_qr_line_amount.filtered(lambda r: r.sequence == next_seq)
        # self.check_next_approver()
        approve_flg = False
        if approved_qr_line_amount:
            for line in approved_qr_line_amount:
                # line.approved_user_ids += self.env.user
                if line.user_id and len(line.user_id) > 0:
                    user_ids = line.mapped('user_id').ids
                    if self._uid in user_ids and (
                            line.min_approver == (len(line.approved_user_ids.ids) + 1) or line.min_approver <= 1):
                        approve_flg = True
                        line.write({'approved': True})
                        return self.request_quote_approve()
                    else:
                        line.approved_user_ids += self.env.user
                        
    @api.multi
    def check_credit_exceed(self):
        self.credit_exceed = False
        invoice_ids = self.env['account.invoice'].search([('partner_id','=',self.partner_id.id), ('state','=','open')])
        total_price = 0
        for rec in invoice_ids:
            total_price += rec.amount_total
        total_price = total_price + self.amount_total 
        if total_price > self.partner_id.credit_limit:
            self.credit_exceed = True
            
        
    @api.multi
    def check_next_approver(self):
        self.is_multiline_approval = True
        if self.credit_approving_matrix_line_ids:
            lines_amount = self.credit_approving_matrix_line_ids.filtered(lambda r: r.approved == False)
            sorted_seq_data = lines_amount.sorted('sequence')
            next_seq = 0
            if sorted_seq_data:
                next_seq = sorted_seq_data[0].sequence
            approved_qr_line_amount = lines_amount.filtered(lambda r: r.sequence == next_seq)
            if approved_qr_line_amount and any(line.min_approver >= 2 for line in approved_qr_line_amount):
                if self.env.user.id in approved_qr_line_amount.mapped('user_id.id') and any(
                        self.env.user.id not in line.approved_user_ids.ids for line in approved_qr_line_amount):
                    self.is_multiline_approval = False
            elif self.env.user.id in approved_qr_line_amount.mapped('user_id.id'):
                self.is_multiline_approval = False

    @api.multi
    def request_approved(self):
        self.write({'state':'to_approved'})
        return

    @api.multi
    def reject(self):
        self.write({'state': 'rejected'})

    @api.model
    def create(self,values):
        res = super(SaleOrder,self).create(values)
#         approver_in_list = False
#         ir_values_obj = self.env['ir.values']
#         block_over_limit = ir_values_obj.get_default('account.config.settings', 'block_over_limit')
#         allow_over_limit = ir_values_obj.get_default('account.config.settings', 'allow_over_limit')
#         approving_matrix = self.env['credit.approving.matrix'].browse(values.get('credit_approving_matrix_id'))
#         for approve_lines in approving_matrix.credit_approving_matrix_ids:
#             if self._uid in approve_lines.user_id.ids:
#                 approver_in_list = True
#         if block_over_limit:
#             invoice_ids = self.env['account.invoice'].search([('partner_id','=',values.get('partner_id')), ('state','=','open')])
#             for rec in invoice_ids:
#                 if rec.partner_id.credit_limit:
#                     total_price = 0
#                     for line in values.get('order_line'):
#                         if line[2].get('price_unit'):
#                             total_price += line[2].get('price_unit')
#                     if total_price > rec.partner_id.credit_limit:
#                         if not approver_in_list or not allow_over_limit:
#                             raise ValidationError(_('You cannot create new sale order exceeding the credit limit of this customer!'))
        return res

    @api.multi
    def write(self,values):
        res = super(SaleOrder,self).write(values)
#         ir_values_obj = self.env['ir.values']
#         approver_in_list = False
#         block_over_limit = ir_values_obj.get_default('account.config.settings', 'block_over_limit')
#         allow_over_limit = ir_values_obj.get_default('account.config.settings', 'allow_over_limit')
#         for approve_lines in self.credit_approving_matrix_line_ids:
#             if self._uid in approve_lines.user_id.ids:
#                 approver_in_list = True
#         if block_over_limit:
#             if not approver_in_list or not allow_over_limit or self.credit_exceed:
#                 raise ValidationError(_('You cannot create new sale order exceeding the credit limit of this customer!'))
        return res

