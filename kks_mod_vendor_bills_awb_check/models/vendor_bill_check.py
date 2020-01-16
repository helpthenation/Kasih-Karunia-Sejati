# -*- coding: utf-8 -*-
import odoo.addons.decimal_precision as dp
from xlrd import open_workbook
import xlwt
import xlsxwriter
from cStringIO import StringIO
from odoo import api, exceptions, fields, models, _, tools, registry
from datetime import datetime
import xlrd ,datetime
import base64
import io
import tempfile

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    '''check_state = fields.Selection([
        ('match', 'Match'),
        ('mismatch', 'Mismatch'),
        ('partial', 'Partially Match'),
    ], string='Check Status', default='mismatch',compute='find_purchase_check_status')'''
    awb = fields.Char('AWB No.',compute='find_awb_no',store=True)
    
    
    
    check_state = fields.Selection([
        ('match', 'Match'),
        ('mismatch', 'Mismatch'),
        ('partial', 'Partially Match'),
    ], string='Check Status', default=False, compute=False)
    
    #@api.depends('vendor_bill_check_line_ids.total_amount')
    @api.multi
    @api.depends('order_line.awb')
    def find_awb_no(self):
        for rec in self:
            awb_lst = []
            if rec.order_line:
                for awb in rec.order_line.mapped('awb'):
                    if awb and awb not in awb_lst:
                        awb_lst.append(awb)
                if awb_lst:
                    rec.awb = ','.join(awb_lst)
        
    '''api.multi
    def find_purchase_check_status(self):
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
                rec.check_state = 'partial'''
    
    '''@api.model
    def _prepare_picking(self):
        for order in self:
            awb_lst = []
            awb = ''
            if any([ptype in ['product', 'consu'] for ptype in order.order_line.mapped('product_id.type')]):
                for awb in order.order_line.mapped('awb'):
                    if awb not in awb_lst:
                        awb_lst.append(awb)
            
            if awb_lst:
                awb = ','.join(awb_lst)

            if not self.group_id:
                self.group_id = self.group_id.create({
                    'name': self.name,
                    'partner_id': self.partner_id.id
                })
            if not self.partner_id.property_stock_supplier.id:
                raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
            return {
                'picking_type_id': self.picking_type_id.id,
                'partner_id': self.partner_id.id,
                'date': self.date_order,
                'origin': self.name,
                'location_dest_id': self._get_destination_location(),
                'location_id': self.partner_id.property_stock_supplier.id,
                'company_id': self.company_id.id,
                'awb':awb,
            }'''
        
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    check_status = fields.Selection([
        ('match', 'Match'),
        ('mismatch', 'Mismatch'),
    ], string='Check Status')
    
    awb = fields.Char('AWB No.')
    
    
class Picking(models.Model):
    _inherit = "stock.picking"

    awb = fields.Char('AWB No.', readonly=True, store=True)
    
        
class VendorBillCheck(models.Model):
    _name='vendor.bill.check'

    state = fields.Selection([
        ('draft', 'New'),
        ('validate', 'Validated'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    name = fields.Char('Name')
    create_date = fields.Datetime(string='Creation Date', readonly=True, index=True,
                                  help="Date on which sales order is created.",default=fields.Datetime.now)
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')

    partner_id = fields.Many2one('res.partner', string='Vendor',required=True, domain="[('supplier','=',True)]")

    order_line = fields.One2many('vendor.bill.check.line', 'order_id', string='Order Lines', copy=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all',
                                 track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always')
    purchase_order_lines_count = fields.Integer(compute='_amount_all',string='Vendor Bills # of items')

    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',readonly=True,
                                   help="Pricelist for current sales order.")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get('sale.order'))

    xls_file = fields.Binary('XLS File')
    datas_fname = fields.Char('File Name')
    vendor_bill_check_line_ids = fields.One2many('vendor.bill.check.excel.data','vendor_bill_check_id','Sales Check Import')
    total_sales_data = fields.Monetary(string='Vendor Statement Amount', store=True, readonly=True, compute='_amount_sales_invoice_all')
    vendor_excel_count = fields.Integer(compute='_amount_sales_invoice_all', string='Vendor statement # of items')

    @api.model
    def create(self, vals):
        code = self.env['ir.sequence'].next_by_code('vendor.bill.check')
        vals.update({'name': code})
        return super(VendorBillCheck, self).create(vals)

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'

    @api.multi
    def action_validate(self):
        for rec in self:
            for order_line in rec.order_line:
                for vendor_bill_check_excel in rec.vendor_bill_check_line_ids:
                    if order_line.awb == vendor_bill_check_excel.awb_exc and order_line.product_uom_qty == vendor_bill_check_excel.qty and order_line.price_total == vendor_bill_check_excel.total_amount:
                        po_line_obj = self.env['purchase.order.line'].browse(order_line.po_line_id.id)
                        po_line_obj.check_status = 'match'
                        order_line.check_state = 'match'
                    else:
                        po_line_obj = self.env['purchase.order.line'].browse(order_line.po_line_id.id)
                        po_line_obj.check_status = 'mismatch'
                        order_line.check_state = 'mismatch'
                
            mismatch_data = rec.order_line.filtered(lambda r: r.check_state != 'match')
            if mismatch_data:
                mismatch_data.write({'check_state':'mismatch'})
        self.state = 'validate'

    @api.multi
    def action_create_invoice(self):
        for rec in self:
            rec.action_validate()
            if rec.order_line:
                purchase_orders = []    
                for order_line in rec.order_line:
                    if order_line.po_id not in purchase_orders:
                        purchase_orders.append(order_line.po_id)
                if purchase_orders:
                    for po in purchase_orders:
                        match_count  = 0
                        mismatch_count = 0
                        for order_line in po.order_line:
                            if order_line.check_status == 'match':
                                match_count +=1
                            else:
                                mismatch_count +=1
                        
                        if len(po.order_line.ids) == match_count:
                            po.check_state = 'match'
                        elif len(po.order_line.ids) == mismatch_count:
                            po.check_state = 'mismatch'
                        else:
                            po.check_state = 'partial'
        
        return True

    @api.onchange('partner_id')
    def onchange_sales_check_partner(self):
        for record in self:
            line_data = []
            for purchase_obj in self.env['purchase.order'].search([('invoice_status','=','to invoice'),('partner_id','=',record.partner_id.id)]):
                for line_obj in purchase_obj.order_line:
                    vals = {}
                    vals.update({
                        'order_id': purchase_obj.id,
                        'name': line_obj.name,
                        'price_unit': line_obj.price_unit,
                        'price_subtotal': line_obj.price_subtotal,
                        'price_total': line_obj.price_total,
                        #'price_reduce': line_obj.price_reduce,
                        'product_uom_qty': line_obj.product_qty,
                        'tax_id' : [(6, 0, line_obj.taxes_id.ids)],
                        #'discount': line_obj.discount,
                        'product_id': line_obj.product_id.id,
                        'product_uom':line_obj.product_uom,
                        'currency_id' : line_obj.currency_id.id,
                        'company_id':line_obj.company_id,
                        #'analytic_tag_ids' : [(6, 0, line_obj.analytic_tag_ids.ids)],
                        'po_line_id': line_obj.id,
                        'po_id': purchase_obj.id,
                        #'partner_shipping_id': line_obj.order_id.partner_shipping_id.id
                        'partner_shipping_id': line_obj.order_id.dest_address_id.id,
                        #'awb':line_obj.order_id.awb,
                        'awb':line_obj.awb,
                    })
                    line_data.append([0,0,vals])
            record.order_line = line_data

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the PO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            count = 0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                count += 1
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    #price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    price = line.price_unit
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'purchase_order_lines_count' : count
            })
            
    @api.depends('vendor_bill_check_line_ids.total_amount')
    def _amount_sales_invoice_all(self):
        """
        Compute the total amounts of the PO.
        """
        for order in self:
            amount_untaxed = 0
            count = 0
            for line in order.vendor_bill_check_line_ids:
                amount_untaxed += line.total_amount
                count +=1

            order.update({
                'total_sales_data': amount_untaxed,
                'vendor_excel_count':count
            })

    @api.multi
    def download_template_excel(self):
        filename = 'VendorBillCheckTemplate.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet('Patients Info')
        style = xlwt.easyxf('font:height 200, bold True, name Arial;align: horiz center; ')

        worksheet.write(0, 0, 'Vendor', style)
        worksheet.write(0, 1, str(self.partner_id.name))

        worksheet.write(2, 0, 'DATE', style)
        worksheet.write(2, 1, 'VENDOR', style)
        worksheet.write(2, 2, 'AWB', style)
        worksheet.write(2, 3, 'NO.QTY', style)
        worksheet.write(2, 4, 'UNIT', style)
        worksheet.write(2, 5, 'UNIT OF MEASURE', style)
        worksheet.write(2, 6, 'UNIT PRICE', style)
        worksheet.write(2, 7, 'TAX PERCENTAGE', style)
        worksheet.write(2, 8, 'TAX AMOUNT', style)
        worksheet.write(2, 9, 'TOTAL', style)
        worksheet.write(2, 10, 'TOTAL AMOUNT', style)

        fp = StringIO()
        workbook.save(fp)
        data = base64.encodestring(fp.getvalue())
        fp.close()

        ids = self.env['ir.attachment'].search([('datas_fname','=','VendorBillCheckTemplate1.xls')]).ids
        if ids:
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            download_url = '/web/content/' + str(ids[0]) + '?download=true'
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
            }

        else:
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            attachment_obj = self.env['ir.attachment']
            attachment_id = attachment_obj.create(
                {'name': 'VendorBillCheck', 'datas_fname': filename , 'datas': data})
            download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
            }


    @api.multi
    def import_vendor_bills_report(self):
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
                if cnt <= 2:
                    cnt += 1
                    continue

                for col in range(sheet.ncols):
                    if first_col:
                        first_col = False
                        inv_date  = sheet.cell_value(row, col)
                        if inv_date:
                            a1_as_datetime = datetime.datetime(*xlrd.xldate_as_tuple(inv_date, wb.datemode))
                            vals.append(str(a1_as_datetime))
                    else:
                        vals.append(sheet.cell_value(row, col))
                excel_data.append(vals)

            matching_data = []
            for obj in rec.order_line:
                vals = {}
                #vals['sku_id'] = obj.sku_id or ''
                vals['awb'] = obj.awb or ''
                vals['date'] = str(obj.po_line_id.order_id.date_order)
                vals['qty'] = obj.product_uom_qty
                #vals['total'] = obj.price_subtotal
                vals['total'] = obj.price_total
                vals['sale_order_line_id'] = obj.po_line_id.id
                vals['sale_check_line_id'] = obj.id
                matching_data.append(vals)
            rec.vendor_bill_check_line_ids.unlink()

            # Excel Data import
            import_data = []
            for dt in excel_data:
                vals = {}
                partner_id = self.env['res.partner'].search([('name','=ilike',dt[1])],limit=1)
                if rec.partner_id.id == partner_id.id:
                    uom_id = self.env['product.uom'].search([('name','ilike',dt[4])],limit=1)
                    is_match = False
                    for match_data in matching_data:
                        price_total = float(dt[6]) + float(dt[8])

                        #if str(dt[2]) == str(match_data.get('sku_id')) and str(dt[0]).split(' ')[0] == str(match_data.get('date')).split(' ')[0] and dt[3] == match_data.get('qty') and price_total == match_data.get('total'):
                        if str(dt[2]) == str(match_data.get('awb')) and dt[3] == match_data.get('qty') and price_total == match_data.get('total'):
                            is_match = True
                            '''po_line_obj = self.env['purchase.order.line'].browse(match_data.get('sale_order_line_id'))
                            po_line_obj.check_status = 'match'

                            vendor_bill_check_line_obj = self.env['vendor.bill.check.line'].browse(
                                match_data.get('sale_check_line_id'))
                            vendor_bill_check_line_obj.check_state = 'match'''
                            break;
                    vals['vendor_date'] = dt[0]
                    vals['partner_id'] = partner_id.id
                    vals['awb_exc'] = str(dt[2])
                    vals['qty'] = dt[3]
                    vals['product_uom'] = uom_id.id
                    vals['price_unit'] = dt[5]
                    vals['sub_total'] = dt[6]
                    vals['tax_percentage'] = dt[7]
                    vals['tax_amount'] = dt[8]
                    vals['is_checked'] = is_match
                    import_data.append([0,0,vals])
            rec.vendor_bill_check_line_ids = import_data

class VendorBillCheckLine(models.Model):
    _name = 'vendor.bill.check.line'
    _description = 'Vendor Bills Check Line'

    order_id = fields.Many2one('vendor.bill.check', string='Order Reference', required=True, ondelete='cascade', index=True,
                               copy=False)

    po_line_id = fields.Many2one('purchase.order.line','Purchase Order Line')
    po_id = fields.Many2one('purchase.order','Purchase Order')
    po_name = fields.Char(related='po_line_id.order_id.name')
    order_date = fields.Datetime(string='Date',related='po_line_id.order_id.date_order')
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

    #discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

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
    #analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    #sku_id = fields.Many2one('sku.sku', string="No.SKU")
    awb = fields.Char('AWB No.')
    currency_id = fields.Many2one("res.currency", related='order_id.currency_id', string="Currency", readonly=True)

    #@api.depends('price_unit', 'discount')
    @api.depends('price_unit')
    def _get_price_reduce(self):
        for line in self:
            #line.price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
            line.price_reduce = line.price_unit 

    @api.depends('price_total', 'product_uom_qty')
    def _get_price_reduce_tax(self):
        for line in self:
            line.price_reduce_taxinc = line.price_total / line.product_uom_qty if line.product_uom_qty else 0.0

    @api.depends('price_subtotal', 'product_uom_qty')
    def _get_price_reduce_notax(self):
        for line in self:
            line.price_reduce_taxexcl = line.price_subtotal / line.product_uom_qty if line.product_uom_qty else 0.0

    #@api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    @api.depends('product_uom_qty', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            #price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            price = line.price_unit
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.partner_shipping_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

class VendorBillCheckExcelDate(models.Model):
    _name = 'vendor.bill.check.excel.data'

    vendor_bill_check_id = fields.Many2one('vendor.bill.check')
    vendor_date = fields.Datetime(string='Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Vendor',readonly=True)
    awb_exc = fields.Char('AWB No.')
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

