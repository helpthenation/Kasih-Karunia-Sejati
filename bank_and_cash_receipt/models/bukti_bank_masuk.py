# -*- coding: utf-8 -*-


from odoo import fields, models, api, _

class BuktiBankMasuk(models.Model):

    _name = 'bukti.bank.masuk'

    name = fields.Char("Name", copy=False, default=lambda self: _('New'))
    ref = fields.Char(string='Reference', copy=False)
    date = fields.Date(required=True,  default=fields.Date.context_today)
    period_id = fields.Many2one('account.period', 'Period', required=False)
    journal_ids = fields.Many2many('account.journal', string='Journal', required=True)
    line_ids = fields.One2many('bukti.bank.masuk.line', 'bukti_id', copy=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'bukti.bank.masuk') or _('New')
        return super(BuktiBankMasuk, self).create(vals)


class BuktiBankMasukLine(models.Model):

    _name = 'bukti.bank.masuk.line'

    name = fields.Char(required=True, string="Label")
    debit = fields.Float()
    account_id = fields.Many2one('account.account', string='Account', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    bukti_id = fields.Many2one('bukti.bank.masuk', ondelete="cascade", index=True, required=True)

