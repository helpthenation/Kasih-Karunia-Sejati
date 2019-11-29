# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta


class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"
    _description = "Account Report Line"
    _order = "sequence"

    def _build_cmp(self, balance, comp):
        if comp != 0:
            res = round((balance - comp) / comp * 100, 1)
            if (res > 0) != self.green_on_positive:
                return (str(res) + '%', 'color: red;')
            else:
                return (str(res) + '%', 'color: green;')
        else:
            return (str(0.0) + '%')

    def _build_cmp_diff(self, balance, comp):
        res = (balance - comp)
        return res

    @api.multi
    def get_lines(self, financial_report, context, currency_table, linesDicts):
        final_result_table = []
        comparison_table = context.get_periods()
        currency_precision = self.env.user.company_id.currency_id.rounding
        # build comparison table

        for line in self:
            res = []
            debit_credit = len(comparison_table) == 1
            domain_ids = {'line'}
            k = 0
            for period in comparison_table:
                period_from = period[0]
                period_to = period[1]
                strict_range = False
                if line.special_date_changer == 'from_beginning':
                    period_from = False
                if line.special_date_changer == 'to_beginning_of_period':
                    date_tmp = datetime.strptime(period[0], "%Y-%m-%d") - relativedelta(days=1)
                    period_to = date_tmp.strftime('%Y-%m-%d')
                    period_from = False
                if line.special_date_changer == 'strict_range':
                    strict_range = True
                r = line.with_context(date_from=period_from, date_to=period_to, strict_range=strict_range)._eval_formula(financial_report, debit_credit, context, currency_table, linesDicts[k])
                debit_credit = False
                res.append(r)
                domain_ids.update(set(r.keys()))
                k += 1
            res = self._put_columns_together(res, domain_ids)
            if line.hide_if_zero and all([float_is_zero(k, precision_rounding=currency_precision) for k in res['line']]):
                continue
            # Post-processing ; creating line dictionnary, building comparison, computing total for extended, formatting
            vals = {
                'id': line.id,
                'name': line.name,
                'type': 'line',
                'level': line.level,
                'footnotes': context._get_footnotes('line', line.id),
                'columns': [abs(i) for i in res['line']],
                'unfoldable': len(domain_ids) > 1 and line.show_domain != 'always',
                'unfolded': line in context.unfolded_lines,
            }
            if line.action_id:
                vals['action_id'] = line.action_id.id
            domain_ids.remove('line')
            lines = [vals]
            groupby = line.groupby or 'aml'
            if line in context.unfolded_lines or line.show_domain == 'always':
                if line.groupby:
                    domain_ids = sorted(list(domain_ids), key=lambda k: line._get_gb_name(k))
                for domain_id in domain_ids:
                    name = line._get_gb_name(domain_id)
                    vals = {
                        'id': domain_id,
                        'name': name and len(name) >= 45 and name[0:40] + '...' or name,
                        'level': 1,
                        'type': groupby,
                        'footnotes': context._get_footnotes(groupby, domain_id),
                        'columns': [abs(i) for i in res[domain_id]],
                    }
                    if line.financial_report_id.name == 'Aged Receivable':
                        vals['trust'] = self.env['res.partner'].browse([domain_id]).trust
                    lines.append(vals)
                if domain_ids:
                    lines.append({
                        'id': line.id,
                        'name': _('Total') + ' ' + line.name,
                        'type': 'o_account_reports_domain_total',
                        'level': 1,
                        'footnotes': context._get_footnotes('o_account_reports_domain_total', line.id),
                        'columns': [abs(i) for i in list(lines[0]['columns'])],
                    })

            for vals in lines:
                if len(comparison_table) == 2:
                    vals['columns'].insert(-1, line._build_cmp_diff(abs(vals['columns'][0]), abs(vals['columns'][1])))
                    vals['columns'].insert(-1, line._build_cmp(abs(vals['columns'][1]), abs(vals['columns'][2])))
                    for i in range(0, len(vals['columns'])):
                        if i != 2:
                            vals['columns'][i] = line._format(abs(vals['columns'][i]))
                elif len(comparison_table) > 2:
                    val_list = []
                    j = 0
                    for i in vals['columns']:
                        val_list.append(line._format(abs(i)))
                        if j < len(vals['columns'])-1:
                            val_list.append(line._format(abs(line._build_cmp_diff(abs(vals['columns'][j]), abs(vals['columns'][j+1])))))
                            val_list.append(line._build_cmp(abs(vals['columns'][j]), abs(vals['columns'][j+1])))
                        j += 1
                    vals['columns'] = val_list
                else:
                    vals['columns'] = map(line._format, [abs(i) for i in vals['columns']])
                if not line.formulas:
                    vals['columns'] = ['' for k in vals['columns']]

            if len(lines) == 1:
                new_lines = line.children_ids.get_lines(financial_report, context, currency_table, linesDicts)
                if new_lines and line.level > 0 and line.formulas:
                    divided_lines = self._divide_line(lines[0])
                    result = [divided_lines[0]] + new_lines + [divided_lines[1]]
                else:
                    result = []
                    if line.level > 0:
                        result += lines
                    result += new_lines
                    if line.level <= 0:
                        result += lines
            else:
                result = lines
            final_result_table += result
        return final_result_table


class AccountFinancialReportContext(models.TransientModel):
    _inherit = "account.financial.html.report.context"
    _description = "A particular context for a financial report"
    # _inherit = "account.report.context.common"

    def get_columns_names(self):
        columns = []
        if self.report_id.debit_credit and not self.comparison:
            columns += [_('Debit'), _('Credit')]
        columns += [self.get_balance_date()]
        if self.comparison:
            if self.periods_number == 1 or self.date_filter_cmp == 'custom':
                columns += [self.get_cmp_date()]
            else:
                columns += self.get_cmp_periods(display=True)
        col_list = []
        if len(columns) == 2:
            columns.insert(-1, 'diff')
            columns.insert(-1, 'diff %')
        elif len(columns) > 2:
            for col in columns:
                col_list.append(col)
                if col != columns[-1]:
                    col_list.append('diff')
                    col_list.append('diff %')
            columns = col_list
        return columns

    @api.multi
    def get_columns_types(self):
        types = []
        if self.report_id.debit_credit and not self.comparison:
            types += ['number', 'number']
        types += ['number']
        if self.comparison:
            if self.periods_number == 1 or self.date_filter_cmp == 'custom':
                types += ['number', 'number', 'number']
            else:
                types += (['number', 'number', 'number'] * self.periods_number)
        return types
