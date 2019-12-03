# -*- coding: utf-8 -*-

from odoo import models, api, _, fields
from odoo.tools.misc import formatLang
import time
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT as DTF


class ReportAgedPartnerBalance(models.AbstractModel):
    _inherit = 'report.account.report_agedpartnerbalance'

    def _get_partner_move_lines2(self, account_type, date_from, target_move, period_length, target_domain):
        report_date_query = '(l.date <= %s)'
        # if self.env.context.get('aging_due_filter_cmp'):
        #     report_date_query = '(l.date_maturity <= %s)'

        periods = {}
        start = datetime.strptime(date_from, "%Y-%m-%d")
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length)
            periods[str(i)] = {
                'name': (i!=0 and (str((5-(i+1)) * period_length) + '-' + str((5-i) * period_length)) or ('+'+str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i!=0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        res = []
        total = []
        cr = self.env.cr
        user_company = self.env.user.company_id.id
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
        arg_list = (tuple(move_state), tuple(account_type))
        #build the reconciliation clause to see what partner needs to be printed
        reconciliation_clause = '(l.reconciled IS FALSE)'
        cr.execute('SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where create_date > %s', (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list += (tuple(reconciled_after_date),)
        arg_list += (date_from, user_company)
        query = '''
            SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
            FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
            WHERE (l.account_id = account_account.id)
                AND (l.move_id = am.id)
                AND (am.state IN %s)
                AND (account_account.internal_type IN %s)
                AND ''' + reconciliation_clause + '''
                AND ''' + report_date_query + '''
                AND l.company_id = %s
                AND l.invoice_id is not NULL
                AND (SELECT state FROM account_invoice WHERE id = l.invoice_id) = 'open'
            ORDER BY UPPER(res_partner.name)'''
        cr.execute(query, arg_list)

        partners = cr.dictfetchall()
        # Add missing partners
        partner_ids = [line.get('partner_id') for line in partners]
        domain = [('partner_id','not in', partner_ids),('partner_id','!=',False),
            ('payment_date','<=',self.env.context.get('date_to')),
            ('state','=','posted'),('move_line_ids','!=',False)]
        if self.env.context.get('account_type') == 'receivable':
            domain.append(('payment_type','=','inbound'))
        else:
            domain.append(('payment_type','=','outbound'))
        domain.append(('company_id', 'in', self.env.context['context_id'].company_ids.ids))
        payment_ids = self.env['account.payment'].search(domain)
        for payment in payment_ids:
            if payment.partner_id.id not in partner_ids:
                partner_ids.append(payment.partner_id.id)
                partners.append({'upper': payment.partner_id.name, 'partner_id': payment.partner_id.id})

        # put a total of 0
        for i in range(7):
            total.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        if not partner_ids:
            return [], [], []

        # This dictionary will store the not due amount of all partners
        undue_amounts = {}
        rate_dict = {}
        currency_dict = {}
        if target_domain:
            query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (SELECT currency_id FROM account_invoice WHERE id = l.invoice_id) in %s
                    AND (account_account.internal_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) > %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND ''' + report_date_query + '''
                AND l.company_id = %s
                AND l.invoice_id is not NULL
                AND (SELECT state FROM account_invoice WHERE id = l.invoice_id) = 'open'
                '''
            cr.execute(query, (tuple(move_state),tuple(target_domain), tuple(account_type), date_from, tuple(partner_ids), date_from, user_company))
        else:
            query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.internal_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) > %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND ''' + report_date_query + '''
                AND l.company_id = %s
                AND l.invoice_id is not NULL
                AND (SELECT state FROM account_invoice WHERE id = l.invoice_id) = 'open'
                '''
            cr.execute(query, (tuple(move_state), tuple(account_type), date_from, tuple(partner_ids), date_from, user_company))
        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [x[0] for x in aml_ids] or []
        aml_ids = self.env['account.move.line'].search([('id', 'in', aml_ids)], order='date')
        for line in aml_ids:
            partner_id = line.partner_id.id or False
            if partner_id not in undue_amounts:
                undue_amounts[partner_id] = 0.0
            line_amount = line.balance
            if line.balance == 0:
                continue
            for partial_line in line.matched_debit_ids:
                if partial_line.create_date[:10] <= date_from:
                    line_amount += partial_line.amount
            for partial_line in line.matched_credit_ids:
                if partial_line.create_date[:10] <= date_from:
                    line_amount -= partial_line.amount
            if not self.env.user.company_id.currency_id.is_zero(line_amount):
                undue_amounts[partner_id] += line_amount
                if line.move_id:
                    currency = self.env['account.invoice'].search([('number','=',line.move_id.name)],limit=1).currency_id
                    currency_dict[partner_id] = currency.name
                lines[partner_id].append({
                    'line': line,
                    'amount': line_amount,
                    'period': 5,
                    'main_period': 0,
                    'amount_currency': abs(line.amount_currency) or line_amount,
                    'amount_residual': abs(line.amount_residual) or line_amount,
                })

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(5):
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            if periods[str(i)]['start'] and periods[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (periods[str(i)]['start'], periods[str(i)]['stop'])
            elif periods[str(i)]['start']:
                dates_query += ' >= %s)'
                args_list += (periods[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(i)]['stop'],)
            args_list += (date_from, user_company)
            if target_domain:
                query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        AND ''' + dates_query + '''
                    AND ''' + report_date_query + '''
                    AND l.company_id = %s
                    AND (SELECT currency_id FROM account_invoice WHERE id = l.invoice_id) in %s
                    AND l.invoice_id is not NULL
                    AND (SELECT state FROM account_invoice WHERE id = l.invoice_id) = 'open'
                    '''
                args_list += (tuple(target_domain),)
            else:
                query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        AND ''' + dates_query + '''
                    AND ''' + report_date_query + '''
                    AND l.company_id = %s
                    AND l.invoice_id is not NULL
                    AND (SELECT state FROM account_invoice WHERE id = l.invoice_id) = 'open'
                    '''
            cr.execute(query, args_list)
            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [x[0] for x in aml_ids] or []
            # Ordering records based on date
            aml_ids = self.env['account.move.line'].search([('id','in',aml_ids)], order='date')
            for line in aml_ids:
                partner_id = line.partner_id.id or False
                if partner_id not in partners_amount:
                    partners_amount[partner_id] = 0.0
                line_amount = line.balance
                if line.balance == 0:
                    continue
                for partial_line in line.matched_debit_ids:
                    if partial_line.create_date[:10] <= date_from:
                        line_amount += partial_line.amount
                for partial_line in line.matched_credit_ids:
                    if partial_line.create_date[:10] <= date_from:
                        line_amount -= partial_line.amount

                if not self.env.user.company_id.currency_id.is_zero(line_amount):
                    due_amount_domain = [('partner_id','=',partner_id)]
                    if account_type and account_type[0] == 'payable':
                        due_amount_domain.append(('type','=','in_invoice'))
                    elif account_type and account_type[0] == 'receivable':
                        due_amount_domain.append(('type', '=', 'out_invoice'))
                    partners_amount[partner_id] += line_amount
                    all_invoice = self.env['account.invoice'].search(due_amount_domain)
                    full_amount = sum(all_invoice.mapped('amount_total'))
                    not_due_amount = full_amount + line_amount
                    lines[partner_id].append({
                        'line': line,
                        'amount': line_amount,
                        'not_due_amount': not_due_amount,
                        'period': i,
                        'amount_currency': abs(line.amount_currency) or line_amount,
                        'amount_residual': abs(line.amount_residual) or line_amount,
                    })
            history.append(partners_amount)

        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            if partner['partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
                undue_amt = undue_amounts[partner['partner_id']]
            total[6] = total[6] + undue_amt
            values['direction'] = undue_amt

            if not float_is_zero(values['direction'], precision_rounding=self.env.user.company_id.currency_id.rounding):
                at_least_one_amount = True

            for i in range(5):
                during = False
                if partner['partner_id'] in history[i]:
                    during = [history[i][partner['partner_id']]]
                # Adding counter
                total[(i)] = total[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
                if not float_is_zero(values[str(i)], precision_rounding=self.env.user.company_id.currency_id.rounding):
                    at_least_one_amount = True
            values['total'] = sum([values['direction']] + [values[str(i)] for i in range(5)])
            ## Add for total
            total[(i + 1)] += values['total']
            values['partner_id'] = partner['partner_id']
            if partner['partner_id']:
                browsed_partner = self.env['res.partner'].browse(partner['partner_id'])
                values['name'] = browsed_partner.name and len(browsed_partner.name) >= 45 and browsed_partner.name[0:40] + '...' or browsed_partner.name
                values['trust'] = browsed_partner.trust
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False
            if not at_least_one_amount:
                domain = [('partner_id','=',partner['partner_id']),
                    ('payment_date','<=',self.env.context.get('date_to')),
                    ('state','=','posted'),('move_line_ids','!=',False)]
                if self.env.context.get('account_type') == 'receivable':
                    domain.append(('payment_type', '=', 'inbound'))
                else:
                    domain.append(('payment_type', '=', 'outbound'))
                domain.append(('company_id','in',self.env.context['context_id'].company_ids.ids))
                payment_ids = self.env['account.payment'].search(domain)
                if payment_ids:
                    at_least_one_amount = True
            if at_least_one_amount:
                res.append(values)
        return res, total, lines


class account_context_aged_receivable(models.TransientModel):
    _inherit = "account.context.aged.receivable"

    def get_columns_names(self):
        context = self.env.context
        if context.get('aging_filter_cmp') and context.get('filter_local_currency'):
            return [[_("Invoice Date")], [_("Due Date")], [1, _("0 - 30")], [1, _("31 - 60")],
                    [1, _("61 - 90")], [1, _("91 - 120")], [1, _(">120")], [_("Local Due")],
                    [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]
            # Aging filter (original currency)
        if context.get('aging_filter_cmp') and context.get('filter_original_currency'):
            return [[_("Invoice Date")], [_("Due Date")], [1, _("0 - 30")], [1, _("31 - 60")],
                    [1, _("61 - 90")], [1, _("91 - 120")], [1, _(">120")], [_("Original Due")],
                    [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]
            # Due aging filter (local currency)
        if context.get('aging_due_filter_cmp') and context.get('filter_local_currency'):
            return [[_("Invoice Date")], [_("Due Date")], [_("Not Due")], [1, _("0 - 30")],
                    [1, _("31 - 60")], [1, _("61 - 90")], [1, _(">90")], [_("Local Due")],
                    [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]
            # Due aging filter (original currency)
        if context.get('aging_due_filter_cmp') and context.get('filter_original_currency'):
            return [[_("Invoice Date")], [_("Due Date")], [_("Not Due")], [1, _("0 - 30")],
                    [1, _("31 - 60")], [1, _("61 - 90")], [1, _(">90")], [_("Original Due")],
                    [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]
            # Aging filter only
        if context.get('aging_filter_cmp'):
            return [[_("Invoice Date")], [_("Due Date")], [_("Current")], [1, _("1 Mth")],
                    [1, _("2 Mth")], [1, _("3 Mth")], [1, _(">3 Mth")], [_("Local Due")],
                    [_("Invoice Amount")], [_("Age")]]
            # Due aging filter only
        if context.get('aging_due_filter_cmp'):
            return [[_("Invoice Date")], [_("Due Date")], [_("Not Due")], [1, _("1 Mth")],
                    [1, _("2 Mth")], [1, _("3 Mth")], [1, _(">3 Mth")], [_("Local Due")],
                    [_("Invoice Amount")], [_("Age")]]
        return [[_("Invoice Date")], [_("Due Date")], [1, _("0 - 30")], [1, _("31 - 60")],
                [1, _("61 - 90")], [1, _("91 - 120")], _([1, ">120"]), [_("Local Due")],
                [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]

    @api.multi
    def get_columns_types(self):
        return ["number", "number", "number", "number", "number","number", "number", "number", "number", "number", "number", "number", "number", "number", "number", "number", "number", "number"]

    def get_due_not_due_column_name(self):
        context = self.env.context
        if context.get('aging_filter_cmp') and context.get('filter_local_currency'):
            return [_("-"), _("-"), _("-"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("-"), _("-"), _("-"), _("-"), _("-")]
        # Aging filter (original currency)
        if context.get('aging_filter_cmp') and context.get('filter_original_currency'):
            return [_("-"), _("-"), _("-"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("-"), _("-"), _("-"), _("-"), _("-")]
        # Due aging filter (local currency)
        if context.get('aging_due_filter_cmp') and context.get('filter_local_currency'):
            return [_("-"), _("-"), _("-"), _("-"), _("Due"), _("Not Due"),
                    _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"),
                    _("-"), _("-"), _("-"), _("-")]
        # Due aging filter (original currency)
        if context.get('aging_due_filter_cmp') and context.get('filter_original_currency'):
            return [_("-"), _("-"), _("-"), _("-"), _("Due"), _("Not Due"),
                    _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("-"), _("-"), _("-"), _("-")]
        # Aging filter only
        if context.get('aging_filter_cmp'):
            return [_("-"), _("-"), _("-"), _("-"), _("Due"), _("Not Due"), _("Due"), _("Not Due"),
                    _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("-"), _("-")]
        # Due aging filter only
        if context.get('aging_due_filter_cmp'):
            return [_("-"), _("-"), _("-"), _("-"), _("Due"), _("Not Due"),
                    _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("-"),
                    _("-")]
        return [_("-"), _("-"), _("-"), _("Due"), _("Not Due"), _("Due"),
                _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"),
                _("Not Due"), _("-"), _("-"), _("-"), _("-"), _("-")]


class AccountContextAgedPayable(models.TransientModel):
    _inherit = "account.context.aged.payable"

    def get_columns_names(self):
        context = self.env.context
        # Aging filter (local currency)
        if context.get('aging_filter_cmp') and context.get('filter_local_currency'):
            return [[_("Invoice Date")], [_("Due Date")], [1, _("0 - 30")], [1, _("31 - 60")],
                    [1, _("61 - 90")], [1, _("91 - 120")], [1, _(">120")], [_("Local Due")],
                    [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]
        # Aging filter (original currency)
        if context.get('aging_filter_cmp') and context.get('filter_original_currency'):
            return [[_("Invoice Date")], [_("Due Date")], [1, _("0 - 30")], [1, _("31 - 60")],
                    [1, _("61 - 90")], [1, _("91 - 120")], [1, _(">120")], [_("Original Due")],
                    [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]
        # Due aging filter (local currency)
        if context.get('aging_due_filter_cmp') and context.get('filter_local_currency'):
            return [[_("Invoice Date")], [_("Due Date")], [_("Not Due")], [1, _("0 - 30")],
                    [1, _("31 - 60")], [1, _("61 - 90")], [1, _(">90")], [_("Local Due")],
                    [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]
        # Due aging filter (original currency)
        if context.get('aging_due_filter_cmp') and context.get('filter_original_currency'):
            return [[_("Invoice Date")], [_("Due Date")], [_("Not Due")], [1, _("0 - 30")],
                    [1, _("31 - 60")], [1, _("61 - 90")], [1, _(">90")], [_("Original Due")],
                    [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]
        # Aging filter only
        if context.get('aging_filter_cmp'):
            return [[_("Invoice Date")], [_("Due Date")], [_("Current")], [1, _("1 Mth")],
                    [1, _("2 Mth")], [1, _("3 Mth")], [1, _(">3 Mth")], [_("Local Due")],
                    [_("Invoice Amount")], [_("Age")]]
        # Due aging filter only
        if context.get('aging_due_filter_cmp'):
            return [[_("Invoice Date")], [_("Due Date")], [_("Not Due")], [1, _("1 Mth")],
                    [1, _("2 Mth")], [1, _("3 Mth")], [1, _(">3 Mth")], [_("Local Due")],
                    [_("Invoice Amount")], [_("Age")]]
        return [[_("Invoice Date")], [_("Due Date")], [1, _("0 - 30")], [1, _("31 - 60")],
                [1, _("61 - 90")], [1, _("91 - 120")], [1, _(">120")], [_("Local Due")],
                [_("Invoice Amount")], [_("Age")], [_("Currency")], [_("Currency Rate")]]


    @api.multi
    def get_columns_types(self):
        return ["number", "number", "number", "number", "number","number", "number", "number", "number", "number", "number", "number", "number", "number", "number", "number", "number", "number"]



    def get_due_not_due_column_name(self):
        context = self.env.context
        if context.get('aging_filter_cmp') and context.get('filter_local_currency'):
            return [_("-"), _("-"), _("-"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("-"), _("-"), _("-"), _("-"), _("-")]
        # Aging filter (original currency)
        if context.get('aging_filter_cmp') and context.get('filter_original_currency'):
            return [_("-"), _("-"), _("-"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("-"), _("-"), _("-"), _("-"), _("-")]
        # Due aging filter (local currency)
        if context.get('aging_due_filter_cmp') and context.get('filter_local_currency'):
            return [_("-"), _("-"), _("-"), _("-"), _("Due"), _("Not Due"),
                    _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"),
                    _("-"), _("-"), _("-"), _("-")]
        # Due aging filter (original currency)
        if context.get('aging_due_filter_cmp') and context.get('filter_original_currency'):
            return [_("-"), _("-"), _("-"), _("-"), _("Due"), _("Not Due"),
                    _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"),
                    _("Not Due"), _("-"), _("-"), _("-"), _("-")]
        # Aging filter only
        if context.get('aging_filter_cmp'):
            return [_("-"), _("-"), _("-"), _("-"), _("Due"), _("Not Due"), _("Due"), _("Not Due"),
                    _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("-"), _("-")]
        # Due aging filter only
        if context.get('aging_due_filter_cmp'):
            return [_("-"), _("-"), _("-"), _("-"), _("Due"), _("Not Due"),
                    _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("-"),
                    _("-")]
        return [_("-"), _("-"), _("-"), _("Due"), _("Not Due"), _("Due"),
                _("Not Due"), _("Due"), _("Not Due"), _("Due"), _("Not Due"), _("Due"),
                _("Not Due"), _("-"), _("-"), _("-"), _("-"), _("-")]

class ReportAccountAgedPartner(models.AbstractModel):
    _inherit = "account.aged.partner"

    @api.model
    def _lines(self, context, line_id=None):
        sign = 1.0
        lines = []
        multi_currency = False
        report_type = self.env.context.get('account_type')
        currency_ids = self._context.get('currency_ids', [])
        results, total, amls = self.env['report.account.report_agedpartnerbalance']._get_partner_move_lines2(
            [self._context['account_type']], self._context['date_to'], 'posted', 30, currency_ids)
        config_setting = self.env['account.config.settings'].search([], order='id desc', limit=1)
        flag = True
        if self.env.context.get('account_type') == 'receivable':
            flag = False
        if config_setting and config_setting.group_multi_currency:
            multi_currency = True

        # Calculate invoice currency amount total
        partner_total_amount = {}
        partner_due_amount = {}

        partner_ids = []
        for line in results:
            partner_ids.append(line.get('partner_id'))
        partner_ids = list(set(partner_ids))

        for partner_id in amls:
            if partner_id in partner_ids:
                for line in amls.get(partner_id):
                    aml = line['line']
                    invoice = self.env['account.invoice'].search([('number', '=', aml.move_id.name)], limit=1)
                    invoice_sign = 1.0
                    if invoice.type in ('out_refund', 'in_refund'):
                        invoice_sign = -1.0
                    # Currency Total
                    if partner_id not in partner_total_amount:
                        partner_total_amount.update(
                            {partner_id: round(invoice_sign * abs(aml.amount_currency or aml.debit or aml.credit), 2)})
                    else:
                        partner_total_amount.update({partner_id: partner_total_amount.get(partner_id) + round(
                            invoice_sign * abs(aml.amount_currency or aml.debit or aml.credit), 2)})

                    # Residual Total
                    if self.env.context.get('filter_original_currency'):
                        if partner_id not in partner_due_amount:
                            partner_due_amount.update({partner_id: round(
                                invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual), 2)})
                        else:
                            partner_due_amount.update({partner_id: partner_due_amount.get(partner_id) + round(
                                invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual), 2)})
                    else:
                        if partner_id not in partner_due_amount:
                            partner_due_amount.update({partner_id: round(invoice_sign * abs(aml.amount_residual), 2)})
                        else:
                            partner_due_amount.update({partner_id: partner_due_amount.get(partner_id) + round(
                                invoice_sign * abs(aml.amount_residual), 2)})
                # Adding receipts and payments total
                domain = [('partner_id', '=', partner_id), ('payment_date', '<=', self.env.context.get('date_to')),
                          ('state', '=', 'posted'), ('move_line_ids', '!=', False)]
                if self.env.context.get('account_type') == 'receivable':
                    domain.append(('payment_type', '=', 'inbound'))
                else:
                    domain.append(('payment_type', '=', 'outbound'))
                domain.append(('company_id', 'in', self.env.context['context_id'].company_ids.ids))
                payment_ids = self.env['account.payment'].search(domain)
                for payment in payment_ids:
                    move_line_ids = payment.move_line_ids.filtered(lambda r: r.account_id.reconcile)
                    for move_line_id in move_line_ids:
                        if move_line_id.reconciled:
                            continue
                        # Currency Total
                        if partner_id not in partner_total_amount:
                            partner_total_amount.update({partner_id: -round(payment.amount, 2)})
                        else:
                            partner_total_amount.update(
                                {partner_id: partner_total_amount.get(partner_id) - round(payment.amount, 2)})
                        # Residual Total
                        if self.env.context.get('filter_original_currency'):
                            if partner_id not in partner_due_amount:
                                partner_due_amount.update({partner_id: -abs(
                                    round(move_line_id.amount_residual_currency or move_line_id.amount_residual, 2))})
                            else:
                                partner_due_amount.update({partner_id: partner_due_amount.get(partner_id) - abs(
                                    round(move_line_id.amount_residual_currency or move_line_id.amount_residual, 2))})
                        else:
                            if partner_id not in partner_due_amount:
                                partner_due_amount.update({partner_id: -abs(round(move_line_id.amount_residual, 2))})
                            else:
                                partner_due_amount.update({partner_id: partner_due_amount.get(partner_id) - abs(
                                    round(move_line_id.amount_residual, 2))})

        # Not due invoices
        partner_not_due_dict = {}
        partner_totals = {}
        partner_totals_final = {0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00, 'n0': 0.00, 'n1': 0.00, 'n2': 0.00, 'n3': 0.00, 'n4': 0.00}
        current_date = datetime.strptime(self._context['date_to'], "%Y-%m-%d")
        for values in results:
            # Not due invoices
            domain = [('partner_id', '=', values['partner_id']), ('date_due', '>', self.env.context.get('date_to')),
                      ('date_invoice', '<=', self.env.context.get('date_to')), ('state', '=', 'open')]
            domain.append(('company_id', 'in', self.env.context['context_id'].company_ids.ids))
            invoice_ids = self.env['account.invoice'].search(domain)
            partner_not_due_dict.update({values['partner_id']: 0.00})
            for invoice in invoice_ids:
                partner_not_due_dict.update(
                    {values['partner_id']: partner_not_due_dict.get(values['partner_id']) + invoice.residual_signed})

            # Total per period
            partner_totals.update({values['partner_id']: {0: 0.00, 'n0': 0.00, 1: 0.00, 'n1': 0.00, 2: 0.00, 'n2': 0.00, 3: 0.00, 'n3': 0.00, 4: 0.00, 'n4': 0.00,}})
            for line in amls[values['partner_id']]:
                aml = line['line']
                invoice = self.env['account.invoice'].search([('number', '=', aml.move_id.name)], limit=1)
                currency_id = invoice.currency_id or self.env.user.company_id.currency_id
                invoice_sign = 1.0
                if invoice.type in ('out_refund', 'in_refund'):
                    invoice_sign = -1.0
                if invoice:
                    currency_rate = invoice.with_context(date=invoice.date_invoice).currency_id.rate
                else:
                    currency_rate = currency_id.rate
                age = current_date - current_date
                if self.env.context.get('aging_due_filter_cmp'):
                    if invoice.date_due:
                        age = current_date - datetime.strptime(invoice.date_due, "%Y-%m-%d")
                elif invoice.date_invoice:
                    age = current_date - datetime.strptime(invoice.date_invoice, "%Y-%m-%d")
                # 0-30 days
                if age.days >= 0 and age.days <= 30:
                    amount = partner_totals.get(values['partner_id']).get(0)
                    if self.env.context.get('filter_original_currency'):
                        due = amount + (invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))
                        # not_due = amount - due
                        partner_totals.get(values['partner_id']).update({0: due})
                        partner_totals_final.update({0: partner_totals_final.get(0) + (
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n0': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n0': partner_totals_final.get('n0') + (invoice_sign) * (
                                                             aml.credit_cash_basis)})
                        else:
                            partner_totals.get(values['partner_id']).update({'n0': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n0': partner_totals_final.get('n0') + (invoice_sign) * (
                                aml.debit_cash_basis)})

                    else:
                        due = amount + (invoice_sign * abs(aml.amount_residual))
                        # not_due = amount - due
                        partner_totals.get(values['partner_id']).update({0: due})
                        partner_totals_final.update({0: partner_totals_final.get(0) + (invoice_sign * abs(aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n0': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n0': partner_totals_final.get('n0') + (invoice_sign * abs(aml.credit_cash_basis))})
                        else:
                            partner_totals.get(values['partner_id']).update({'n0': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update(
                                {'n0': partner_totals_final.get('n0') + (invoice_sign * abs(aml.debit_cash_basis))})

                # 30-60 days
                if age.days >= 31 and age.days <= 60:
                    amount = partner_totals.get(values['partner_id']).get(1)
                    if self.env.context.get('filter_original_currency'):
                        partner_totals.get(values['partner_id']).update(
                            {1: amount + (invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        partner_totals_final.update({1: partner_totals_final.get(1) + (
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n1': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n1': partner_totals_final.get('n1') + (invoice_sign * (aml.credit_cash_basis))})
                        else:
                            partner_totals.get(values['partner_id']).update({'n1': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n1': partner_totals_final.get('n1') + (invoice_sign * (aml.debit_cash_basis))})
                    else:
                        partner_totals.get(values['partner_id']).update({1: amount + (invoice_sign * abs(aml.amount_residual))})
                        partner_totals_final.update(
                            {1: partner_totals_final.get(1) + (invoice_sign * abs(aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n1': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n1': partner_totals_final.get('n1') + (invoice_sign * abs(aml.credit_cash_basis))})
                        else:
                            partner_totals.get(values['partner_id']).update({'n1': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n1': partner_totals_final.get('n1') + (invoice_sign * abs(aml.debit_cash_basis))})
                # 60-90 days
                if age.days >= 61 and age.days <= 90:
                    amount = partner_totals.get(values['partner_id']).get(2)
                    if self.env.context.get('filter_original_currency'):
                        partner_totals.get(values['partner_id']).update(
                            {2: amount + (invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        partner_totals_final.update({2: partner_totals_final.get(2) + (
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n2': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n2': partner_totals_final.get('n2') + (invoice_sign * (aml.credit_cash_basis))})
                        else:
                            partner_totals.get(values['partner_id']).update({'n2': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n2': partner_totals_final.get('n2') + (invoice_sign * (aml.debit_cash_basis))})
                    else:
                        partner_totals.get(values['partner_id']).update({2: amount + (invoice_sign * abs(aml.amount_residual))})
                        partner_totals_final.update({2: partner_totals_final.get(2) + (invoice_sign * abs(aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n2': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n2': partner_totals_final.get('n2') + (invoice_sign * abs(aml.credit_cash_basis))})
                        else:
                            partner_totals.get(values['partner_id']).update({'n2': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n2': partner_totals_final.get('n2') + (invoice_sign * abs(aml.debit_cash_basis))})
                # 90-120 days
                if age.days >= 91 and age.days <= 120:
                    amount = partner_totals.get(values['partner_id']).get(3)
                    if self.env.context.get('filter_original_currency'):
                        partner_totals.get(values['partner_id']).update({3: amount + (invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        partner_totals_final.update({3: partner_totals_final.get(3) + (invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n3': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n3': partner_totals_final.get('n3') + (invoice_sign * (aml.credit_cash_basis))})
                        else:

                            partner_totals.get(values['partner_id']).update({'n3': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n3': partner_totals_final.get('n3') + (invoice_sign * (aml.debit_cash_basis))})
                    else:
                        partner_totals.get(values['partner_id']).update(
                            {3: amount + (invoice_sign * abs(aml.amount_residual))})
                        partner_totals_final.update(
                            {3: partner_totals_final.get(3) + (invoice_sign * abs(aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n3': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n3': partner_totals_final.get('n3') + (invoice_sign * abs(aml.credit_cash_basis))})
                        else:
                            partner_totals.get(values['partner_id']).update({'n3': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n3': partner_totals_final.get('n3') + (invoice_sign * abs(aml.debit_cash_basis))})
                # >120 days
                if age.days > 120:
                    amount = partner_totals.get(values['partner_id']).get(4)
                    if self.env.context.get('filter_original_currency'):
                        partner_totals.get(values['partner_id']).update(
                            {4: amount + (invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        partner_totals_final.update({4: partner_totals_final.get(4) + (
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n4': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n4': partner_totals_final.get('n4') + (invoice_sign * (aml.credit_cash_basis))})
                        else:

                            partner_totals.get(values['partner_id']).update({'n4': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n4': partner_totals_final.get('n4') + (invoice_sign * (aml.debit_cash_basis))})
                    else:
                        partner_totals.get(values['partner_id']).update({4: amount + (invoice_sign * abs(aml.amount_residual))})
                        partner_totals_final.update({4: partner_totals_final.get(4) + (invoice_sign * abs(aml.amount_residual))})
                        if flag:
                            partner_totals.get(values['partner_id']).update({'n4': aml.credit_cash_basis or 0.0})
                            partner_totals_final.update({'n4': partner_totals_final.get('n4') + (invoice_sign * abs(aml.credit_cash_basis))})
                        else:
                            partner_totals.get(values['partner_id']).update({'n4': aml.debit_cash_basis or 0.0})
                            partner_totals_final.update({'n4': partner_totals_final.get('n4') + (invoice_sign * abs(aml.debit_cash_basis))})

            # Receipts and Payments
            domain = [('partner_id', '=', values['partner_id']),
                      ('payment_date', '<=', self.env.context.get('date_to')), ('state', '=', 'posted'),
                      ('move_line_ids', '!=', False)]
            if self.env.context.get('account_type') == 'receivable':
                domain.append(('payment_type', '=', 'inbound'))
            else:
                domain.append(('payment_type', '=', 'outbound'))
            domain.append(('company_id', 'in', self.env.context['context_id'].company_ids.ids))
            payment_ids = self.env['account.payment'].search(domain)
            for payment in payment_ids:
                move_line_ids = payment.move_line_ids.filtered(lambda r: r.account_id.reconcile)
                for move_line_id in move_line_ids:
                    if move_line_id.reconciled:
                        continue
                    age = current_date - datetime.strptime(payment.payment_date, "%Y-%m-%d")

                    # 0-30 days
                    if age.days >= 0 and age.days <= 30:
                        amount = partner_totals.get(values['partner_id']).get(0)
                        if self.env.context.get('filter_original_currency'):
                            partner_totals.get(values['partner_id']).update({0: amount + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            partner_totals_final.update({0: partner_totals_final.get(0) + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n0': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n0': partner_totals_final.get('n0') + -abs(
                                                                 move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n0': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n0': partner_totals_final.get('n0') + -abs(
                                    move_line_id.debit_cash_basis)})

                        else:
                            partner_totals.get(values['partner_id']).update(
                                {0: amount + -abs(move_line_id.amount_residual)})
                            partner_totals_final.update(
                                {0: partner_totals_final.get(0) + -abs(move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n0': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n0': partner_totals_final.get('n0') + -abs(move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n0': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n0': partner_totals_final.get('n0') + -abs(move_line_id.debit_cash_basis)})

                    # 30-60 days
                    if age.days >= 31 and age.days <= 60:
                        amount = partner_totals.get(values['partner_id']).get(1)
                        if self.env.context.get('filter_original_currency'):
                            partner_totals.get(values['partner_id']).update({1: amount + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            partner_totals_final.update({1: partner_totals_final.get(1) + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n1': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n1': partner_totals_final.get('n1') + -abs(
                                                                 move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n1': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n1': partner_totals_final.get('n1') + -abs(
                                    move_line_id.debit_cash_basis)})
                        else:
                            partner_totals.get(values['partner_id']).update(
                                {1: amount + -abs(move_line_id.amount_residual)})
                            partner_totals_final.update(
                                {1: partner_totals_final.get(1) + -abs(move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n1': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n1': partner_totals_final.get('n1') + -abs(move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n1': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n1': partner_totals_final.get('n1') + -abs(move_line_id.debit_cash_basis)})
                    # 60-90 days
                    if age.days >= 61 and age.days <= 90:
                        amount = partner_totals.get(values['partner_id']).get(2)
                        if self.env.context.get('filter_original_currency'):
                            partner_totals.get(values['partner_id']).update({2: amount + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            partner_totals_final.update({2: partner_totals_final.get(2) + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n2': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n2': partner_totals_final.get('n2') + -abs(
                                                                 move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n2': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n2': partner_totals_final.get('n2') + -abs(
                                                                 move_line_id.debit_cash_basis)})
                        else:
                            partner_totals.get(values['partner_id']).update(
                                {2: amount + -abs(move_line_id.amount_residual)})
                            partner_totals_final.update(
                                {2: partner_totals_final.get(2) + -abs(move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n2': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n2': partner_totals_final.get('n2') + -abs(move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n2': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n2': partner_totals_final.get('n2') + -abs(move_line_id.debit_cash_basis)})
                    # 90-120 days
                    if age.days >= 91 and age.days <= 120:
                        amount = partner_totals.get(values['partner_id']).get(3)
                        if self.env.context.get('filter_original_currency'):
                            partner_totals.get(values['partner_id']).update({3: amount + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            partner_totals_final.update({3: partner_totals_final.get(3) + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n3': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n3': partner_totals_final.get('n3') + -abs(
                                                                 move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n3': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n3': partner_totals_final.get('n3') + -abs(
                                                                 move_line_id.debit_cash_basis)})
                        else:
                            partner_totals.get(values['partner_id']).update({3: amount + (invoice_sign * abs(aml.amount_residual))})
                            partner_totals_final.update({3: partner_totals_final.get(3) + -abs(move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n3': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n3': partner_totals_final.get('n3') + -abs(move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n3': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n3': partner_totals_final.get('n3') + -abs(move_line_id.debit_cash_basis)})
                    # >120 days
                    if age.days > 120:
                        amount = partner_totals.get(values['partner_id']).get(4)
                        if self.env.context.get('filter_original_currency'):
                            partner_totals.get(values['partner_id']).update({4: amount + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            partner_totals_final.update({4: partner_totals_final.get(4) + -abs(
                                move_line_id.amount_residual_currency or move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n4': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n4': partner_totals_final.get('n4') + -abs(
                                                                 move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n4': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n4': partner_totals_final.get('n4') + -abs(
                                                                 move_line_id.debit_cash_basis)})
                        else:
                            partner_totals.get(values['partner_id']).update(
                                {4: amount + -abs(move_line_id.amount_residual)})
                            partner_totals_final.update(
                                {4: partner_totals_final.get(4) + -abs(move_line_id.amount_residual)})
                            if flag:
                                partner_totals.get(values['partner_id']).update({'n4': aml.credit_cash_basis or 0.0})
                                partner_totals_final.update({'n4': partner_totals_final.get('n4') + -abs(move_line_id.credit_cash_basis)})
                            else:
                                partner_totals.get(values['partner_id']).update({'n4': aml.debit_cash_basis or 0.0})
                                partner_totals_final.update({'n4': partner_totals_final.get('n4') + -abs(move_line_id.debit_cash_basis)})

        for values in results:
            if not partner_due_amount.get(values['partner_id']):
                continue
            partner_total_line = partner_totals.get(values['partner_id'])

            columns = [partner_total_line[0], partner_total_line['n0'],
                       partner_total_line[1], partner_total_line['n1'],
                       partner_total_line[2], partner_total_line['n2'],
                       partner_total_line[3], partner_total_line['n3'],
                       partner_total_line[4], partner_total_line['n4']]
            if self.env.context.get('aging_due_filter_cmp'):
                columns = [partner_not_due_dict.get(values['partner_id']), partner_total_line[0], partner_total_line['n0'],
                           partner_total_line[1], partner_total_line['n1'],
                           partner_total_line[2], partner_total_line['n2'],
                           partner_total_line[3], partner_total_line['n3'],
                           partner_total_line[4] + partner_total_line['n4']]

            if line_id and values['partner_id'] != line_id:
                continue
            customer = self.env['res.partner'].browse(values['partner_id'])
            if context.show_all == False:
                unfold_value = False
            else:
                unfold_value = values['partner_id'] and (
                            values['partner_id'] in context.unfolded_partners.ids) or context.show_all or False
            vals = {
                'id': values['partner_id'] and values['partner_id'] or -1,
                'name': values['name'],
                'level': 0 if values['partner_id'] else 2,
                'type': values['partner_id'] and 'partner_id' or 'line',
                'footnotes': context._get_footnotes('partner_id', values['partner_id']),
                'columns': columns,
                'multi_currency': multi_currency,
                'trust': values['trust'],
                'unfoldable': values['partner_id'] and True or False,
                'unfolded': unfold_value,
            }
            vals['columns'] = [self._format(t) for t in vals['columns']]
            if self.env.context.get('filter_original_currency'):
                vals['columns'].extend([self._format(partner_due_amount.get(values['partner_id']))])
                vals['columns'].extend([self._format(sign * partner_total_amount.get(values['partner_id'])), ''])
            else:
                vals['columns'].extend([self._format(partner_due_amount.get(values['partner_id']))])
                vals['columns'].extend([self._format(sign * partner_total_amount.get(values['partner_id'])), ''])
            if self.env.context.get('filter_local_currency') or self.env.context.get('filter_original_currency'):
                vals['columns'].extend(['', ''])
            lines.append(vals)

            if self.env.context.get('show_all') != False and (
                    values['partner_id'] in context.unfolded_partners.ids or context.show_all):
                for line in amls[values['partner_id']]:
                    aml = line['line']
                    vals = {
                        'id': aml.id,
                        'name': aml.move_id.name if aml.move_id.name else '/',
                        'move_id': aml.move_id.id,
                        'partnerid': values['partner_id'],
                        'action': aml.get_model_id_and_name(),
                        'multi_currency': multi_currency,
                        'level': 1,
                        'type': 'move_line_id',
                        'footnotes': context._get_footnotes('move_line_id', aml.id),
                    }

                    invoice = self.env['account.invoice'].search([('number', '=', aml.move_id.name)], limit=1)
                    currency_id = invoice.currency_id or self.env.user.company_id.currency_id
                    if invoice:
                        currency_rate = invoice.with_context(date=invoice.date_invoice).currency_id.rate
                    else:
                        currency_rate = currency_id.rate
                    invoice_sign = 1.0
                    if invoice.type in ('out_refund', 'in_refund'):
                        invoice_sign = -1.0
                    age = current_date - current_date
                    if self.env.context.get('aging_due_filter_cmp'):
                        if invoice.date_due:
                            age = current_date - datetime.strptime(invoice.date_due, "%Y-%m-%d")
                    elif invoice.date_invoice:
                        age = current_date - datetime.strptime(invoice.date_invoice, "%Y-%m-%d")

                    # Calculating period based amount
                    if self.env.context.get('aging_due_filter_cmp'):
                        if invoice.date_due:
                            cmp_date_due = datetime.strptime(invoice.date_due, "%Y-%m-%d")
                            if cmp_date_due <= current_date:
                                final_columns = ['']
                                due_date = current_date
                                report_date = datetime.strptime(self.env.context.get('date_to'), "%Y-%m-%d")
                                if invoice.date_due:
                                    due_date = datetime.strptime(invoice.date_due, "%Y-%m-%d")
                                # 0-30 days
                                if (age.days >= 0 and age.days <= 30) or (due_date > report_date):
                                    if self.env.context.get('filter_original_currency'):
                                        final_columns.append(self._format(
                                            invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                                    else:
                                        final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                                    if flag:
                                        final_columns.append(aml.credit_cash_basis or 0.0)
                                    else:
                                        final_columns.append(aml.debit_cash_basis or 0.0)
                                else:
                                    final_columns.extend(['', ''])
                                # 30-60 days
                                if age.days >= 31 and age.days <= 60 and due_date <= report_date:
                                    if self.env.context.get('filter_original_currency'):
                                        final_columns.append(self._format(
                                            invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                                    else:
                                        final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                                    if flag:
                                        final_columns.append(aml.credit_cash_basis or 0.0)
                                    else:
                                        final_columns.append(aml.debit_cash_basis or 0.0)
                                else:
                                    final_columns.extend(['', ''])
                                # 60-90 days
                                if age.days >= 61 and age.days <= 90 and due_date <= report_date:
                                    if self.env.context.get('filter_original_currency'):
                                        final_columns.append(self._format(
                                            invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                                    else:
                                        final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                                    if flag:
                                        final_columns.append(aml.credit_cash_basis or 0.0)
                                    else:
                                        final_columns.append(aml.debit_cash_basis or 0.0)
                                else:
                                    final_columns.extend(['', ''])
                                # >90 days
                                if age.days > 90 and due_date <= report_date:
                                    if self.env.context.get('filter_original_currency'):
                                        final_columns.append(self._format(
                                            invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                                    else:
                                        final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                                    if flag:
                                        final_columns.append(aml.credit_cash_basis or 0.0)
                                    else:
                                        final_columns.append(aml.debit_cash_basis or 0.0)
                                else:
                                    final_columns.extend(['', ''])
                    else:
                        final_columns = []
                        # 0-30 days
                        if age.days >= 0 and age.days <= 30:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                            else:
                                final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                            if flag:
                                final_columns.append(aml.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(aml.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])
                        # 30-60 days
                        if age.days >= 31 and age.days <= 60:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                            else:
                                final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                            if flag:
                                final_columns.append(aml.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(aml.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])
                        # 60-90 days
                        if age.days >= 61 and age.days <= 90:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                            else:
                                final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                            if flag:
                                final_columns.append(aml.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(aml.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])
                        # 90-120 days
                        if age.days >= 91 and age.days <= 120:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                            else:
                                final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                            if flag:
                                final_columns.append(aml.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(aml.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])
                        # >120 days
                        if age.days > 120:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)))
                            else:
                                final_columns.append(self._format(invoice_sign * abs(aml.amount_residual)))
                            if flag:
                                final_columns.append(aml.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(aml.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])

                    # Update total
                    invoice_date = invoice.date_invoice and datetime.strptime(invoice.date_invoice,
                                                                              '%Y-%m-%d').strftime('%d-%m-%Y')
                    due_date = invoice.date_due and datetime.strptime(invoice.date_due, '%Y-%m-%d').strftime('%d-%m-%Y')
                    if due_date:
                        cmp_date_due = datetime.strptime(invoice.date_due, "%Y-%m-%d")

                    if (not self.env.context.get('aging_due_filter_cmp')) or (
                            due_date and (cmp_date_due <= current_date)):
                        vals['columns'] = [invoice_date, due_date]
                        vals['columns'].extend(final_columns)
                        if self.env.context.get('filter_original_currency'):
                            vals['columns'].extend([self._format(
                                invoice_sign * abs(aml.amount_residual_currency or aml.amount_residual)) or ''])
                            vals['columns'].extend([self._format(
                                invoice_sign * abs(aml.amount_currency or aml.debit or aml.credit)) or ''])
                        else:
                            vals['columns'].extend([self._format(invoice_sign * abs(aml.amount_residual)) or ''])
                            vals['columns'].extend([self._format(
                                invoice_sign * abs(aml.amount_currency or aml.debit or aml.credit)) or ''])
                        vals['columns'].extend([(age.days if age.days > 0 else '0')])
                        if self.env.context.get('filter_local_currency') or self.env.context.get(
                                'filter_original_currency'):
                            vals['columns'].extend([invoice.currency_id.name or '', currency_rate or 0.0])
                        lines.append(vals)

                # Receipts and Payments
                domain = [('partner_id', '=', values['partner_id']),
                          ('payment_date', '<=', self.env.context.get('date_to')), ('state', '=', 'posted'),
                          ('move_line_ids', '!=', False)]
                if self.env.context.get('account_type') == 'receivable':
                    domain.append(('payment_type', '=', 'inbound'))
                else:
                    domain.append(('payment_type', '=', 'outbound'))
                domain.append(('company_id', 'in', self.env.context['context_id'].company_ids.ids))
                payment_ids = self.env['account.payment'].search(domain)
                for payment in payment_ids:
                    move_line_ids = payment.move_line_ids.filtered(lambda r: r.account_id.reconcile)
                    for move_line_id in move_line_ids:
                        if move_line_id.reconciled:
                            continue
                        age = current_date - datetime.strptime(payment.payment_date, "%Y-%m-%d")
                        currency_rate = payment.with_context(date=payment.payment_date).currency_id.rate

                        vals = {
                            'id': move_line_id.id,
                            'name': payment.name or '/',
                            'move_id': move_line_id.move_id.id,
                            'partnerid': values['partner_id'],
                            'action': move_line_id.get_model_id_and_name(),
                            'multi_currency': multi_currency,
                            'level': 1,
                            'type': 'move_line_id',
                            'footnotes': context._get_footnotes('move_line_id', move_line_id.id),
                        }

                        final_columns = []
                        # 0-30 days
                        if age.days >= 0 and age.days <= 30:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    -abs(move_line_id.amount_residual_currency or move_line_id.amount_residual)))
                            else:
                                final_columns.append(self._format(-abs(move_line_id.amount_residual)))
                            if flag:
                                final_columns.append(move_line_id.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(move_line_id.debit_cash_basis or 0.0)

                        else:
                            final_columns.extend(['', ''])
                        # 30-60 days
                        if age.days >= 31 and age.days <= 60:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    -abs(move_line_id.amount_residual_currency or move_line_id.amount_residual)))
                            else:
                                final_columns.append(self._format(-abs(move_line_id.amount_residual)))
                            if flag:
                                final_columns.append(move_line_id.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(move_line_id.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])
                        # 60-90 days
                        if age.days >= 61 and age.days <= 90:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    -abs(move_line_id.amount_residual_currency or move_line_id.amount_residual)))
                            else:
                                final_columns.append(self._format(-abs(move_line_id.amount_residual)))
                            if flag:
                                final_columns.append(move_line_id.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(move_line_id.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])
                        # 90-120 days
                        if age.days >= 91 and age.days <= 120:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    -abs(move_line_id.amount_residual_currency or move_line_id.amount_residual)))
                            else:
                                final_columns.append(self._format(-abs(move_line_id.amount_residual)))
                            if flag:
                                final_columns.append(move_line_id.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(move_line_id.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])
                        # >120 days
                        if age.days > 120:
                            if self.env.context.get('filter_original_currency'):
                                final_columns.append(self._format(
                                    -abs(move_line_id.amount_residual_currency or move_line_id.amount_residual)))
                            else:
                                final_columns.append(self._format(-abs(move_line_id.amount_residual)))
                            if flag:
                                final_columns.append(move_line_id.credit_cash_basis or 0.0)
                            else:
                                final_columns.append(move_line_id.debit_cash_basis or 0.0)
                        else:
                            final_columns.extend(['', ''])

                        # Update total
                        payment_date = datetime.strptime(payment.payment_date, '%Y-%m-%d').strftime('%d-%m-%Y')

                        vals['columns'] = [payment_date, '']
                        vals['columns'].extend(final_columns)
                        if self.env.context.get('filter_original_currency'):
                            vals['columns'].extend([self._format(
                                -abs(move_line_id.amount_residual_currency or move_line_id.amount_residual)) or ''])
                            vals['columns'].extend([self._format(-abs(payment.amount)) or ''])
                        else:
                            vals['columns'].extend([self._format(-abs(move_line_id.amount_residual)) or ''])
                            vals['columns'].extend([self._format(-abs(payment.amount)) or ''])
                        vals['columns'].extend([(age.days if age.days > 0 else '0')])
                        if self.env.context.get('filter_local_currency') or self.env.context.get(
                                'filter_original_currency'):
                            vals['columns'].extend([payment.currency_id.name or '', currency_rate or 0.0])
                        lines.append(vals)
                partner_total_line = partner_totals.get(values['partner_id'])
                columns = [partner_total_line[0], partner_total_line['n0'], partner_total_line[1], partner_total_line['n1'],
                           partner_total_line[2], partner_total_line['n2'], partner_total_line[3], partner_total_line['n3'],
                           partner_total_line[4], partner_total_line['n4'],]
                if self.env.context.get('aging_due_filter_cmp'):
                    columns = [partner_not_due_dict.get(values['partner_id']), partner_total_line[0], partner_total_line['n0'],
                               partner_total_line[1], partner_total_line['n1'],
                               partner_total_line[2], partner_total_line['n2'],
                               partner_total_line[3], partner_total_line['n3'],
                               partner_total_line[4] + partner_total_line['n4'],]

                vals1 = {
                    'id': values['partner_id'],
                    'type': 'o_account_reports_domain_total',
                    'name': _('Total'),
                    'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total',
                                                                               values['partner_id']),
                    'columns': columns,
                    'level': 1,
                }
                final_columns1 = [self._format(t) for t in vals1['columns']]
                vals1['columns'] = ['', '']
                vals1['columns'].extend(final_columns1)
                if self.env.context.get('filter_original_currency'):
                    vals1['columns'].extend([self._format(sign * partner_due_amount.get(values['partner_id']))])
                    vals1['columns'].extend([self._format(sign * partner_total_amount.get(values['partner_id'])), ''])
                else:
                    vals1['columns'].extend([self._format(sign * partner_due_amount.get(values['partner_id']))])
                    vals1['columns'].extend([self._format(sign * partner_total_amount.get(values['partner_id'])), ''])
                if self.env.context.get('filter_local_currency') or self.env.context.get('filter_original_currency'):
                    vals1['columns'].extend(['', ''])
                lines.append(vals1)

        if total and not line_id:
            currency_total = sum(partner_total_amount.values())
            columns = [partner_totals_final[0], partner_totals_final['n0'], partner_totals_final[1], partner_totals_final['n1'],
                       partner_totals_final[2], partner_totals_final['n2'], partner_totals_final[3], partner_totals_final['n3'],
                       partner_totals_final[4], partner_totals_final['n4']]
            if self.env.context.get('aging_due_filter_cmp'):
                columns = [sum(partner_not_due_dict.values()), partner_totals_final[0], partner_totals_final['n0'],
                           partner_totals_final[1], partner_totals_final['n1'],
                           partner_totals_final[2], partner_totals_final['n2'],
                           partner_totals_final[3], partner_totals_final['n3'],
                           partner_totals_final[4] + partner_totals_final['n4']]

            total_line = {
                'id': 0,
                'name': _('Total'),
                'level': 0,
                'multi_currency': multi_currency,
                'type': 'o_account_reports_domain_total',
                'footnotes': context._get_footnotes('o_account_reports_domain_total', 0),
                'columns': columns,
            }
            final_columns = [self._format(t) for t in total_line['columns']]
            total_line['columns'] = ['', '']
            total_line['columns'].extend(final_columns)
            if self.env.context.get('filter_original_currency'):
                total_line['columns'].extend(
                    [self._format(sign * sum([float("%.2f" % x) for x in partner_due_amount.values()]))])
                total_line['columns'].extend([self._format(sign * currency_total), ''])
            else:
                total_line['columns'].extend(
                    [self._format(sign * sum([float("%.2f" % x) for x in partner_due_amount.values()]))])
                total_line['columns'].extend([self._format(sign * currency_total), ''])
            if self.env.context.get('filter_local_currency') or self.env.context.get('filter_original_currency'):
                total_line['columns'].extend(['', ''])
            lines.append(total_line)
        partner_not_due_amount = {}
        for partner, amt in partner_total_amount.items():
            partner_not_due_amount.update({partner: amt - partner_due_amount.get(partner)})

        return lines
