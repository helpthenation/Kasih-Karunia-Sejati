# -*- coding: utf-8 -*-


from odoo import fields, models, api, _

class BuktiKasKeluar(models.Model):

    _name = 'bukti.kas.keluar'

    name = fields.Char("Name", copy=False, default=lambda self: _('New'))
    ref = fields.Char(string='Reference', copy=False)
    date = fields.Date(required=True,  default=fields.Date.context_today)
    period_id = fields.Many2one('account.period', 'Period', required=False)
    journal_ids = fields.Many2many('account.journal', string='Journal', required=True)
    line_ids = fields.One2many('bukti.kas.keluar.line', 'bukti_id', copy=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'bukti.kas.keluar') or _('New')
        return super(BuktiKasKeluar, self).create(vals)


class BuktiKasKeluarLine(models.Model):

    _name = 'bukti.kas.keluar.line'

    name = fields.Char(required=True, string="Label")
    credit = fields.Float()
    account_id = fields.Many2one('account.account', string='Account', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    bukti_id = fields.Many2one('bukti.kas.keluar.wiz', ondelete="cascade", index=True, required=True)

