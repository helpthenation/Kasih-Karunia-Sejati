# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class Inventory(models.Model):
    _inherit = "stock.inventory"

    date = fields.Datetime('Inventory Date', readonly=False, required=True, default=fields.Datetime.now,
        help="The date that will be used for the stock level check of the products and the validation of the stock move related to this inventory.")
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Rejected'),
        ('confirm', 'In Progress'),
        ('missed','Missed Item'),
        ('lock','Lock'),
        ('done', 'Validated')],
        copy=False, index=True, readonly=True,
        default='draft')
    approved_by = fields.Many2one('hr.employee', string="Approved by")

    @api.multi
    def action_calculate_inventory(self):
        for line in self.line_ids:
            if line.product_qty==0:
                raise UserError(_('Product real quantity can not be 0'))
        self.write({'state': 'missed'})

    def notify_email_manager(self):
            # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            menu_id = self.env['ir.model.data'].get_object_reference('stock', 'menu_action_inventory_form')[1]
            action_id =  self.env['ir.model.data'].get_object_reference('stock','action_inventory_form')[1]
            url = base_url + "/web?#id="+ str(self.id) +"&view_type=form&model=stock.inventory&menu_id="+str(menu_id)+"&action=" + str(action_id)

            email_from = self.env.user.company_id.email or 'Administrator <admin@example.com>'
            # email_from = 'Administrator <admin@example.com>'
            email_to = self.approved_by.work_email
            subject = 'Notification : You have an Invenotory Adjustment to Approve'
            message = """
                    <html>
                        <head>
                            Dear %s,
                        </head>
                        <body>
                            <span>
                                You have Inventory Adjustment<a href="%s" target="_blank">(Monthly Stock Opanme)</a> waiting for your approval <br/>
                                Requestor : <b> %s </b> 
                                Thank You,
                            </span>
                        </body> 
                    <html>""" % (self.approved_by.name, url, self.env.user.name)

            vals = {
                'state': 'outgoing',
                'subject': subject,
                'body_html': '<pre>%s</pre>' % message,
                'email_to': email_to,
                'email_from': email_from,
            }
            partner_ids = [self.env.user.partner_id.id, self.approved_by.user_id.id and self.approved_by.user_id.partner_id.id]
            mail_message = {
                'subject': subject,
                'body': '<pre>%s</pre>' % message,
                'partner_ids': [(6, 0, partner_ids)],
                'needaction_partner_ids': [(6, 0, partner_ids)]
            }
            thread_pool = self.env['mail.message'].create(mail_message)
            thread_pool.needaction_partner_ids = [(6, 0, partner_ids)]

            if vals:
                email_id = self.env['mail.mail'].create(vals)
                if email_id:
                    email_id.send()

    @api.multi
    def action_request_approve(self):
        self.write({'state': 'lock'})
        self.notify_email_manager()

class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    @api.depends('theoretical_qty','product_qty')
    def _compute_missed_item(self):
        for rec in self:
            rec.missed_item = rec.theoretical_qty - rec.product_qty

    missed_item = fields.Float('Missed Item', compute="_compute_missed_item")