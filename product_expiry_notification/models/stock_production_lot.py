from odoo import models,fields,api
import base64
import datetime as DT

class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    expiry_days = fields.Integer('expiry Days before', default=7)

    @api.model
    def sent_email_expiry(self):
        Mail = self.env['mail.mail']
        email_template = self.env['ir.model.data'].get_object('product_expiry_notification',
                                                              'email_template_product_expiry')
        today = DT.date.today()
        lots = self.search([('life_date', '!=', False)])
        expired_lots = '<span>Recapitulation of all list lot of product thats already expired </span> <br/>'
        for lot in lots:
            expiry_days = 7
            life_date = DT.datetime.strptime(lot.life_date, "%Y-%m-%d %H:%M:%S")
            if lot.expiry_days:
                expiry_days = lot.expiry_days
            notification_date = life_date - DT.timedelta(days=expiry_days)
            if notification_date.date() <= today:
                expired_lots += '<span>'+ lot.name + ' of product name ' + lot.product_id.name + '</span><br/>'

        values = {
            'model': 'stock.production.lot',
            'res_id': False,
            'subject': email_template.subject,
            'body': '',
            'body_html': email_template.body_html + expired_lots,
            'parent_id': None,
            'email_from': email_template.email_from,
                    # 'auto_delete': True,
            'email_to': email_template.email_to,
            'email_cc': email_template.email_cc
            }
        Mail.create(values).send()
