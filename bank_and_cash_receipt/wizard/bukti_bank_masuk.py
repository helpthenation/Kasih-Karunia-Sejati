# -*- coding: utf-8 -*-


from odoo import fields, models, api

class BuktiBankMasukWiz(models.Model):

    _name = 'bukti.bank.masuk.wiz'

    @api.model
    def _default_journal(self):
        journals = self.env['account.journal'].search([('type', '=', 'bank')])
        if journals:
            return journals[0]
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
        res = super(BuktiBankMasukWiz, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if self.env.context.get('active_model') == 'account.move' and active_ids:
            move_ids = self.env['account.move'].browse(
                self.env.context.get('active_ids'))
            lines = []
            for move in move_ids:
                for line in move.line_ids:
                    if move.journal_id.id == res.get('journal_id'):
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
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, default=_default_journal)
    line_ids = fields.One2many('bukti.bank.masuk.line.wiz', 'bukti_id', copy=True)

    @api.multi
    def create_data(self):
        lines = []
        for rec in self.line_ids:
            lines.append({'name':rec.name,
                          'account_id':rec.account_id.id,
                          'partner_id':rec.partner_id.id,
                          'debit':rec.debit})
        self.env['bukti.bank.masuk'].create({'journal_id':self.journal_id.id,
                                                'date': self.date,
                                                'period_id':self.period_id.id,
                                                'ref':self.ref,
                                                'line_ids':[(0, 0, l) for l in lines]})


class BuktiBankMasukLineWiz(models.Model):

    _name = 'bukti.bank.masuk.line.wiz'

    name = fields.Char(required=True, string="Label")
    debit = fields.Float()
    account_id = fields.Many2one('account.account', string='Account', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    bukti_id = fields.Many2one('bukti.bank.masuk.wiz', ondelete="cascade", index=True, required=True)

