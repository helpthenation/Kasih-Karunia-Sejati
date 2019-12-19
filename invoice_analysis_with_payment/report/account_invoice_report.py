from __future__ import division
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import ustr
from datetime import datetime,timedelta

class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'
    
    
    amount_paid = fields.Float(string='Amount Paid', readonly=True)
    residual = fields.Float(string='Amount Due', readonly=True)
    number = fields.Char(string='Number', readonly=True)
    name = fields.Char(string='Reference', readonly=True)
    
    _depends = {
        'account.invoice': [
            'account_id', 'amount_total_company_signed', 'commercial_partner_id', 'company_id',
            'currency_id', 'date_due', 'date_invoice', 'fiscal_position_id',
            'journal_id', 'partner_bank_id', 'partner_id', 'payment_term_id',
            'residual','amount_paid','number','name', 'state', 'type', 'user_id',
        ],
        'account.invoice.line': [
            'account_id', 'invoice_id', 'price_subtotal', 'product_id',
            'quantity', 'uom_id', 'account_analytic_id',
        ],
        'product.product': ['product_tmpl_id'],
        'product.template': ['categ_id'],
        'product.uom': ['category_id', 'factor', 'name', 'uom_type'],
        'res.currency.rate': ['currency_id', 'name'],
        'res.partner': ['country_id'],
    }

    def _select(self):
        select_str = """
            SELECT sub.id, sub.date, sub.product_id, sub.partner_id, sub.country_id, sub.account_analytic_id,
                sub.payment_term_id, sub.uom_name, sub.currency_id, sub.journal_id,
                sub.fiscal_position_id, sub.user_id, sub.company_id, sub.nbr, sub.type, sub.state,
                sub.weight, sub.volume,
                sub.categ_id, sub.date_due, sub.amount_paid, sub.account_id, sub.account_line_id, sub.partner_bank_id,
                sub.product_qty, sub.number,sub.name, sub.price_total as price_total, sub.price_average as price_average,
                COALESCE(cr.rate, 1) as currency_rate, sub.residual as residual, sub.commercial_partner_id as commercial_partner_id
        """
        return select_str

    def _sub_select(self):
        select_str = """
                SELECT ail.id AS id,
                    ai.date_invoice AS date,
                    ail.product_id, ai.partner_id, ai.payment_term_id, ail.account_analytic_id,
                    u2.name AS uom_name,
                    ai.currency_id, ai.journal_id, ai.fiscal_position_id, ai.user_id, ai.company_id,
                    1 AS nbr,
                    ai.type, ai.state, pt.categ_id, ai.date_due, ai.account_id, ail.account_id AS account_line_id,
                    ai.partner_bank_id, ai.amount_paid, ai.number, ai.name,
                    SUM ((invoice_type.sign * ail.quantity) / u.factor * u2.factor) AS product_qty,
                    SUM(ail.price_subtotal_signed) AS price_total,
                    SUM(ABS(ail.price_subtotal_signed)) / CASE
                            WHEN SUM(ail.quantity / u.factor * u2.factor) <> 0::numeric
                               THEN SUM(ail.quantity / u.factor * u2.factor)
                               ELSE 1::numeric
                            END AS price_average,
                    ai.residual_company_signed / (SELECT count(*) FROM account_invoice_line l where invoice_id = ai.id) *
                    count(*) * invoice_type.sign AS residual,
                    ai.commercial_partner_id as commercial_partner_id,
                    partner.country_id,
                    SUM(pr.weight * (invoice_type.sign*ail.quantity) / u.factor * u2.factor) AS weight,
                    SUM(pr.volume * (invoice_type.sign*ail.quantity) / u.factor * u2.factor) AS volume
        """
        return select_str

    def _from(self):
        from_str = """
                FROM account_invoice_line ail
                JOIN account_invoice ai ON ai.id = ail.invoice_id
                JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                LEFT JOIN product_product pr ON pr.id = ail.product_id
                left JOIN product_template pt ON pt.id = pr.product_tmpl_id
                LEFT JOIN product_uom u ON u.id = ail.uom_id
                LEFT JOIN product_uom u2 ON u2.id = pt.uom_id
                JOIN (
                    -- Temporary table to decide if the qty should be added or retrieved (Invoice vs Refund) 
                    SELECT id,(CASE
                         WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN -1
                            ELSE 1
                        END) AS sign
                    FROM account_invoice ai
                ) AS invoice_type ON invoice_type.id = ai.id
        """
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ail.id, ail.product_id, ail.account_analytic_id, ai.date_invoice, ai.id,
                    ai.partner_id, ai.payment_term_id, u2.name, u2.id, ai.currency_id, ai.journal_id,
                    ai.fiscal_position_id, ai.user_id, ai.company_id, ai.type, invoice_type.sign, ai.state, pt.categ_id,
                    ai.date_due, ai.account_id, ail.account_id, ai.partner_bank_id, ai.residual_company_signed,
                    ai.amount_total_company_signed, ai.commercial_partner_id, ai.amount_paid, ai.number, ai.name, partner.country_id
        """
        return group_by_str
    
    


        
