# -*- coding: utf-8 -*-
from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from xlrd import open_workbook
from odoo import api, exceptions, fields, models, _, tools, registry
from odoo.osv import osv
from odoo.exceptions import UserError, ValidationError
import xlrd ,datetime
import base64
import io
import tempfile

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    check_state = fields.Selection([
        ('match', 'Match'),
        ('mismatch', 'Mismatch'),
        ('partial', 'Partially Match'),
    ], string='Check Status', default='mismatch',compute='find_sales_check_status')

    api.multi
    def find_sales_check_status(self):
        for rec in self:
            match_count  = 0
            mismatch_count = 0
            for order_line in rec.order_line:
                if order_line.check_status == 'match':
                    match_count +=1
                else:
                    mismatch_count +=1
            if len(rec.order_line.ids) == match_count:
                rec.check_state = 'match'
            elif len(rec.order_line.ids) == mismatch_count:
                rec.check_state = 'mismatch'
            else:
                rec.check_state = 'partial'

class sales_check(models.Model):
    _name='sales.check'

    state = fields.Selection([
        ('draft', 'New'),
        ('validate', 'Validated'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    name = fields.Char()
    create_date = fields.Datetime(string='Creation Date', readonly=True, index=True,
                                  help="Date on which sales order is created.",default=fields.Datetime.now)
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')

    partner_id = fields.Many2one('res.partner', string='Customer',required=True)

    order_line = fields.One2many('sales.check.line', 'order_id', string='Order Lines', copy=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all',
                                 track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always')
    sale_order_lines_count = fields.Integer(compute='_amount_all',string='Sales # of items')

    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',readonly=True,
                                   help="Pricelist for current sales order.")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get('sale.order'))

    xls_file = fields.Binary('XLS File')
    datas_fname = fields.Char('File Name')
    sales_check_line_ids = fields.One2many('sales.check.excel.data','sales_check_id','Sales Check Import')
    total_sales_data = fields.Monetary(string='Customer Statement Amount', store=True, readonly=True, compute='_amount_sales_invoice_all')
    customer_excel_count = fields.Integer(compute='_amount_sales_invoice_all', string='Customer statement # of items')

    @api.model
    def create(self, vals):
        code = self.env['ir.sequence'].next_by_code('sales.check')
        vals.update({'name': code})
        return super(sales_check, self).create(vals)

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'

    @api.multi
    def action_validate(self):
        self.state = 'validate'

    @api.multi
    def action_create_invoice(self):
        return True
        # invoice_line_data = []
        # for rec in self.sales_check_line_ids:
        #     if rec.is_checked:
        #         account_id = self.env['ir.property'].get('property_account_income_categ_id', 'product.category')
        #
        #         if not account_id:
        #             raise UserError(
        #                 _(
        #                     'There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %
        #                 (rec.product_id.name,))
        #
        #         vals = {
        #             'name': rec.product_id.name,
        #             'origin': rec.sales_check_id.name,
        #             'account_id': account_id and account_id.id,
        #             'price_unit': rec.product_id.list_price,
        #             'quantity': rec.qty,
        #             'discount': 0.0,
        #             'uom_id': rec.product_id.uom_id.id,
        #             'product_id': rec.product_id.id,
        #         }
        #
        #         invoice_line_data.append([0,0,vals])
        #
        #
        # if  invoice_line_data:
        #     invoice = self.env['account.invoice'].create({
        #         'name': self.name,
        #         'origin': self.name,
        #         'type': 'out_invoice',
        #         'reference': False,
        #         'account_id': self.partner_id.property_account_receivable_id.id,
        #         'partner_id': self.partner_id.id,
        #         'invoice_line_ids':invoice_line_data
        #     })


    @api.onchange('partner_id')
    def onchange_sales_check_partner(self):
        for record in self:
            line_data = []
            for sale_obj in self.env['sale.order'].search([('invoice_status','=','to invoice'),('partner_id','=',record.partner_id.id)]):
                for line_obj in sale_obj.order_line:
                    vals = {}
                    vals.update({
                        'order_id': sale_obj.id,
                        'name': line_obj.name,
                        'price_unit': line_obj.price_unit,
                        'price_subtotal': line_obj.price_subtotal,
                        'price_total': line_obj.price_total,
                        'price_reduce': line_obj.price_reduce,
                        'product_uom_qty': line_obj.product_uom_qty,
                        'tax_id' : [(6, 0, line_obj.tax_id.ids)],
                        'discount': line_obj.discount,
                        'product_id': line_obj.product_id.id,
                        'product_uom':line_obj.product_uom,
                        'currency_id' : line_obj.currency_id.id,
                        'company_id':line_obj.company_id,
                        'analytic_tag_ids' : [(6, 0, line_obj.analytic_tag_ids.ids)],
                        'so_line_id': line_obj.id,
                        'partner_shipping_id': line_obj.order_id.partner_shipping_id.id
                    })
                    line_data.append([0,0,vals])
            record.order_line = line_data

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            count = 0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                count += 1
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'sale_order_lines_count' : count
            })

    @api.depends('sales_check_line_ids.total_amount')
    def _amount_sales_invoice_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = 0
            count = 0
            for line in order.sales_check_line_ids:
                amount_untaxed += line.total_amount
                count +=1

            order.update({
                'total_sales_data': amount_untaxed,
                'customer_excel_count':count
            })

    @api.multi
    def import_customer_sales_import(self):
        for rec in self:
            excel_data = []
            datafile = rec.xls_file
            file_name = str(rec.datas_fname)
            # Checking for Suitable File
            if not datafile or not file_name.lower().endswith(('.xls', '.xlsx',)):
                raise exceptions.UserError(_("Please Select an .xls or its compatible file to Import"))
            xls_data = base64.decodestring(datafile)
            temp_path = tempfile.gettempdir()
            # writing a file to temp. location
            fp = open(temp_path + '/xsl_file.xls', 'wb+')
            fp.write(xls_data)
            fp.close()
            # opening a file form temp. location
            wb = open_workbook(temp_path + '/xsl_file.xls')
            sheet = wb.sheet_by_index(0)

            sheet.cell_value(0, 0)

            cnt = 0
            for row in range(sheet.nrows):
                vals = []
                first_col = True
                if cnt < 2:
                    cnt += 1
                    continue
                for col in range(sheet.ncols):
                    if first_col:
                        first_col = False
                        inv_date  = sheet.cell_value(row, col)
                        a1_as_datetime = datetime.datetime(*xlrd.xldate_as_tuple(inv_date, wb.datemode))
                        vals.append(str(a1_as_datetime))
                    else:
                        vals.append(sheet.cell_value(row, col))
                excel_data.append(vals)

            matching_data = []
            for obj in rec.order_line:
                vals = {}
                vals['sku_id'] = obj.sku_id or ''
                vals['date'] = str(obj.so_line_id.order_id.date_order)
                vals['qty'] = obj.product_uom_qty
                vals['total'] = obj.price_subtotal
                vals['sale_order_line_id'] = obj.so_line_id.id
                vals['sale_check_line_id'] = obj.id
                matching_data.append(vals)

            rec.sales_check_line_ids.unlink()

            # Excel Data import
            import_data = []
            for dt in excel_data:
                vals = {}
                partner_id = self.env['res.partner'].search([('name','=',dt[1])],limit=1)
                if rec.partner_id.id == partner_id.id:
                    uom_id = self.env['product.uom'].search([('name','ilike',dt[4])],limit=1)
                    is_match = False
                    for match_data in matching_data:
                        price_total = float(dt[6]) + float(dt[8])

                        if str(dt[2]) == str(match_data.get('sku_id')) and str(dt[0]).split(' ')[0] == str(match_data.get('date')).split(' ')[0] and dt[3] == match_data.get('qty') and price_total == match_data.get('total'):
                            is_match = True
                            sale_line_obj = self.env['sale.order.line'].browse(match_data.get('sale_order_line_id'))
                            sale_line_obj.check_status = 'match'

                            sale_check_line_obj = self.env['sales.check.line'].browse(
                                match_data.get('sale_check_line_id'))
                            sale_check_line_obj.check_state = 'match'
                            break;
                    vals['customer_date'] = dt[0]
                    vals['partner_id'] = partner_id.id
                    vals['sku_number'] = str(dt[2])
                    vals['qty'] = dt[3]
                    vals['product_uom'] = uom_id.id
                    vals['price_unit'] = dt[5]
                    vals['sub_total'] = dt[6]
                    vals['tax_percentage'] = dt[7]
                    vals['tax_amount'] = dt[8]
                    vals['is_checked'] = is_match
                    import_data.append([0,0,vals])
            rec.sales_check_line_ids = import_data

class SalesCheckLine(models.Model):
    _name = 'sales.check.line'
    _description = 'Sales Check Line'

    order_id = fields.Many2one('sales.check', string='Order Reference', required=True, ondelete='cascade', index=True,
                               copy=False)

    so_line_id = fields.Many2one('sale.order.line','Sale Order Line')
    so_name = fields.Char(related='so_line_id.order_id.name')
    order_date = fields.Datetime(string='Date',related='so_line_id.order_id.confirmation_date')
    state = fields.Selection([
        ('draft', 'New'),
        ('validate', 'Validated'),
        ('cancel', 'Cancelled'),
    ], string='Status', related='order_id.state')

    check_state = fields.Selection([
        ('match', 'match'),
        ('mismatch', 'mismatch'),
    ], string='Status')
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)

    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])
    price_reduce_taxinc = fields.Monetary(compute='_get_price_reduce_tax', string='Price Reduce Tax inc', readonly=True,
                                          store=True)
    price_reduce_taxexcl = fields.Monetary(compute='_get_price_reduce_notax', string='Price Reduce Tax excl',
                                           readonly=True, store=True)

    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict', required=True)
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
                                   default=1.0)
    product_uom = fields.Many2one('product.uom', string='Unit of Measure')

    qty_delivered = fields.Float(string='Delivered', copy=False, digits=dp.get_precision('Product Unit of Measure'),
                                 default=0.0)
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True)
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address')
    qty_to_invoice = fields.Float(
        compute='_get_to_invoice_qty', string='To Invoice', store=True, readonly=True,
        digits=dp.get_precision('Product Unit of Measure'))
    qty_invoiced = fields.Float(
        compute='_get_invoice_qty', string='Invoiced', store=True, readonly=True,
        digits=dp.get_precision('Product Unit of Measure'))



    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    sku_id = fields.Many2one('sku.sku', string="No.SKU")
    currency_id = fields.Many2one("res.currency", related='order_id.currency_id', string="Currency", readonly=True)

    @api.depends('price_unit', 'discount')
    def _get_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_unit * (1.0 - line.discount / 100.0)

    @api.depends('price_total', 'product_uom_qty')
    def _get_price_reduce_tax(self):
        for line in self:
            line.price_reduce_taxinc = line.price_total / line.product_uom_qty if line.product_uom_qty else 0.0

    @api.depends('price_subtotal', 'product_uom_qty')
    def _get_price_reduce_notax(self):
        for line in self:
            line.price_reduce_taxexcl = line.price_subtotal / line.product_uom_qty if line.product_uom_qty else 0.0

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.partner_shipping_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

class SalesCheckExcelDate(models.Model):
    _name = 'sales.check.excel.data'

    sales_check_id = fields.Many2one('sales.check')
    customer_date = fields.Datetime(string='Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer',readonly=True)
    sku_number = fields.Char('SKU')
    qty = fields.Float('Qty')
    product_uom = fields.Many2one('product.uom', string='Unit of Measure')
    price_unit = fields.Float('Unit Price', digits=dp.get_precision('Product Price'), default=0.0)
    tax_percentage = fields.Float(string='Tax Percentage', readonly=True, store=True)
    tax_amount = fields.Float('Tax Amount')
    sub_total = fields.Float(string='Total', readonly=True, store=True)
    total_amount = fields.Float(compute='_compute_amount',string='Total Amount')
    is_checked = fields.Boolean('Checked')

    @api.depends('tax_amount', 'price_unit','qty')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            line.update({
                'total_amount': line.tax_amount + line.sub_total
            })

SalesCheckExcelDate()

class SalesOrderLine(models.Model):
    _inherit = 'sale.order.line'

    check_status = fields.Selection([
        ('match', 'Match'),
        ('mismatch', 'Mismatch'),
    ], string='Check Status')