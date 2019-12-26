# -*- coding: utf-8 -*-


from odoo import fields, models, api

class BuktiKasMasukWiz(models.Model):

    _name = 'bukti.kas.masuk.wiz'

    @api.model
    def _default_journal(self):
        journals = self.env['account.journal'].search([('type', '=', 'cash')])
        if journals:
            return journals
        return self.env['account.journal']
    
    def _get_period(self):
        period_obj = self.env['account.period']
        for move in self:
            if move.date:
                move.period_id = period_obj.search(
                    [('date_stop', '>=', move.date), ('date_start', '<=', move.date), ('state', '=', 'draft'), ('special','=',False)],
                    limit=1)
            else:
                move.period_id = period_obj.search([('state', '=', 'draft')], limit=1)

    @api.depends('date')
    @api.onchange('date')
    def _compute_period(self):
        period_obj = self.env['account.period']
        for move in self:
            if move.date:
                move.period_id = period_obj.search(
                    [('date_stop', '>=', move.date), ('date_start', '<=', move.date), ('state', '=', 'draft')],
                    limit=1)
            else:
                move.period_id = period_obj.search([('state', '=', 'draft')], limit=1)

    @api.model
    def default_get(self, fields):
        res = super(BuktiKasMasukWiz, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        lines = []
        if self.env.context.get('active_model') == 'account.move' and active_ids and res.get('journal_ids'):
            move_ids = self.env['account.move'].browse(
                self.env.context.get('active_ids'))
            for move in move_ids:
                if move.journal_id.id in res.get('journal_ids')[0][2]:
                    for line in move.line_ids:
                        if line.debit:
                            lines.append({'account_id':line.account_id.id,
                                          'partner_id':line.partner_id.id,
                                          'name':line.name,
                                          'debit':line.debit})
        res.update({'line_ids': [(0, 0, l) for l in lines]})
        return res

    @api.multi
    @api.depends('period_id')
    @api.onchange('period_id')
    def _get_period(self):
        for ml in self:
            if ml.period_id.state == "done":
                raise UserError(_("You can not change journal entries when the period is closed"))

    ref = fields.Char(string='Reference', copy=False)
    date = fields.Date(required=True,  default=fields.Date.context_today)
    period_id = fields.Many2one('account.period', 'Period', required=False,
                                default=_get_period, compute='_compute_period')
    journal_ids = fields.Many2many('account.journal', string='Journal', required=True, default=_default_journal)
    line_ids = fields.One2many('bukti.kas.masuk.line.wiz', 'bukti_id', copy=True)

    @api.multi
    def create_data(self):
        lines = []
        for rec in self.line_ids:
            lines.append({'name':rec.name,
                          'account_id':rec.account_id.id,
                          'partner_id':rec.partner_id.id,
                          'debit':rec.debit})
        obj = self.env['bukti.kas.masuk'].create({'journal_ids':[(6, 0, self.journal_ids.ids)],
                                            'date': self.date,
                                            'period_id':self.period_id.id,
                                            'ref':self.ref,
                                            'line_ids':[(0, 0, l) for l in lines]})
        form_view = self.env.ref('bank_and_cash_receipt.view_bukti_kas_masuk_form')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bukti.kas.masuk',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(form_view.id, 'form')],
            'res_id': obj.id,
        }


class BuktiKasMasukLineWiz(models.Model):

    _name = 'bukti.kas.masuk.line.wiz'

    name = fields.Char(required=True, string="Label")
    debit = fields.Float()
    account_id = fields.Many2one('account.account', string='Account', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    bukti_id = fields.Many2one('bukti.kas.masuk.wiz', ondelete="cascade", index=True, required=True)

