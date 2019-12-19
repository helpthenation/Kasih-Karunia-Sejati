# -*- coding: utf-8 -*-

from odoo import fields, models, api,_


class BuktiBankKeluar(models.Model):

    _name = 'bukti.bank.keluar'

    name = fields.Char("Name", copy=False, default=lambda self: _('New'))
    ref = fields.Char(string='Reference', copy=False)
    date = fields.Date(required=True,  default=fields.Date.context_today)
    period_id = fields.Many2one('account.period', 'Period', required=False)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    line_ids = fields.One2many('bukti.bank.keluar.line', 'bukti_id')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'bukti.bank.keluar') or _('New')
        return super(BuktiBankKeluar, self).create(vals)


class BuktiBankKeluarLine(models.Model):

    _name = 'bukti.bank.keluar.line'

    name = fields.Char(required=True, string="Label")
    credit = fields.Float()
    account_id = fields.Many2one('account.account', string='Account', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    bukti_id = fields.Many2one('bukti.bank.keluar', ondelete="cascade", index=True, required=True)
