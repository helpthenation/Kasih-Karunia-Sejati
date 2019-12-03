from odoo import models, fields, api, tools
from datetime import datetime, date
from odoo.exceptions import ValidationError

class StockCount(models.Model):
    _name = 'stock.count'
    _inherit = ['mail.thread']
    _description = 'Stock Count'
    _order = 'id desc'

    name = fields.Char('Reference', copy=False, default='/', required=True)
    state = fields.Selection([('open', 'Open'), ('cancel', 'Cancelled'), ('in_progress', 'In Progress'), ('close', 'Closed')], copy=False, track_visibility='onchange', default='open', string='Status')
    count_date = fields.Date('Count Date', copy=False, default=date.today())
    remarks = fields.Text('Notes')
    inventoried_product = fields.Selection([
        ('all_products', 'Scan All Product'), ('specific_category', 'Specific Category'), ('specific_product', 'Specific Product'),
        ('manual', 'Manual')], default='all_products', string='Inventoried Product')
    product_id = fields.Many2one('product.product', string='Product')
    inventoried_category = fields.Many2one('product.category', string='Inventoried Category')
    allow_other_category = fields.Boolean(string='Allow User to Scan Other Category')
    other_category = fields.Many2one('product.category', string='Other Category')
    location_id = fields.Many2one('stock.location', required=True, domain="[('usage', '=', 'internal')]", string='Location')
    line_ids = fields.One2many('stock.count.line', 'count_id', string='Lines')
    product = fields.Char(compute='_compute_product', search='_search_by_product', string='Product')
    inv_id = fields.Many2one('stock.inventory', copy=False, string='Inventory Adjustment')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.count')
        return super(StockCount, self).create(vals)

    def get_count_list(self):
        data_list = []
        for count_id in self.env['stock.count'].search([('state', 'in', ['draft', 'in_progress'])]):
            vals = {}
            vals['id'] = count_id.id
            vals['name'] = count_id.name
            vals['state'] = dict(count_id.fields_get(['state'])['state']['selection'])[count_id.state]
            vals['date'] = str(count_id.count_date)
            vals['location'] = count_id.location_id.name_get()[0][1]
            vals['inventoried_product'] = dict(count_id.fields_get(['inventoried_product'])['inventoried_product']['selection'])[count_id.inventoried_product]
            vals['product'] = count_id.product_id.name if count_id.product_id else ''
            vals['inventoried_category'] = count_id.inventoried_category.name_get()[0][1] if count_id.inventoried_category else ''
            vals['other_category'] = count_id.other_category.name_get()[0][1] if count_id.other_category else ''
            data_list.append(vals)
        return data_list

    def get_count_data(self):
        data_list = []
        for line in self.line_ids:
            vals = {}
            vals['line_id'] = line.id
            vals['product_id'] = line.product_id.id
            vals['product'] = line.product_id.name
            vals['barcode'] = line.product_id.barcode or ''
            vals['item_no'] = line.product_id.default_code or ''
            vals['tracking'] = line.product_id.tracking
            vals['scanned_qty'] = line.count_qty
            vals['scanned_list'] = []
            if line.product_id.tracking != 'none':
                vals['scanned_list'] = [{'lot_name': x.lot_id.name if x.lot_id else '', 'qty': x.qty} for x in line.count_lot_ids]
            data_list.append(vals)
        return data_list

    def action_push_data(self, data_list):
        try:
            for data in data_list:
                if data.get('line_id', False):
                    line_id = self.env['stock.count.line'].browse(data['line_id'])
                else:
                    line_id = self.env['stock.count.line'].create({'count_id': self.id, 'product_id': data.get('product_id')})
                line_id.count_lot_ids.unlink()
                scanned_list = []
                if line_id.product_id.tracking != 'none':
                    for lot_dict in data.get('scanned_data', []):
                        if lot_dict.get('qty', 0):
                            vals = {}
                            lot_id = self.env['stock.production.lot'].search([('product_id', '=', line_id.product_id.id), ('name', '=', lot_dict.get('lot_name', ''))], limit=1)
                            if not lot_id:
                                lot_id = self.env['stock.production.lot'].create({'name': lot_dict.get('lot_name', ''), 'product_id': line_id.product_id.id})
                            vals['product_id'] = line_id.product_id.id
                            vals['lot_id'] = lot_id.id
                            vals['qty'] = lot_dict.get('qty', 0)
                            scanned_list.append((0, 0, vals))
                line_id.write({'count_qty': data.get('qty', 0), 'count_lot_ids': scanned_list})
            return 'True'
        except Exception as e:
            self.env.cr.rollback()
            return str(tools.ustr(e)).replace('\nNone', '')

    @api.onchange('inventoried_product', 'allow_other_category')
    def onchange_inventoried_product(self):
        if self.inventoried_product == 'all_products':
            self.product_id = False
            self.inventoried_category = False
            self.allow_other_category = False
            self.other_category = False
        else:
            if self.inventoried_product != 'specific_product':
                self.product_id = False
            if self.inventoried_product != 'specific_category':
                self.inventoried_category = False
            if not self.allow_other_category:
                self.other_category = False

    def _compute_product(self):
        for record in self:
            record.product = False

    def _search_by_product(self, operator, value):
        product_ids = self.env['product.product'].search(['|', ('name', 'ilike', value), ('default_code', '=', value)]).ids
        ids = []
        if product_ids:
            for line_id in self.env['stock.count.line'].search([('product_id', 'in', product_ids), ('count_id', '!=', False)]):
                if line_id.count_id.id not in ids:
                    ids.append(line_id.count_id.id)
        return [('id', 'in', ids)]

    def get_internal_location(self):
        return [x.name_get()[0][1] for x in self.env['stock.location'].search([('usage', '=', 'internal')])]

    def get_location_id(self, location_name):
        for location_id in self.env['stock.location'].search([('usage', '=', 'internal')]):
            if location_id.name_get()[0][1] == location_name:
                return location_id.id
        return False

    def action_recount(self):
        for record in self:
            record.line_ids.action_recount()

    def search_batch_no(self, product_id, lot_name):
        lot_id = self.env['stock.production.lot'].search([('product_id', '=', int(product_id)), ('name', '=', str(lot_name))], limit=1)
        if lot_id:
            vals = {}
            vals['lot_id'] = lot_id.id
            vals['lot_name'] = lot_id.name
            return vals
        return {}

    def stock_count_without_tracking(self, product_id, location, qty):
        if not product_id or not qty:
            return False
        try:
            vals = {}
            vals['product_id'] = int(product_id)
            vals['qty'] = qty
            vals['user_id'] = self.env.user.id
            vals['location_id'] = self.get_location_id(location)
            self.env['stock.count.quant'].create(vals)
            return True
        except:
            return False

    def update_stock_count(self, product_id, location, lot_list):
        if not product_id or not lot_list:
            return False
        try:
            for data in lot_list:
                if data.get('qty', 0) > 0 and data.get('lot_name', False):
                    location_id = self.get_location_id(location)
                    lot_id = self.env['stock.production.lot'].search([('product_id', '=', int(product_id)), ('name', '=', str(data.get('lot_name', '')))], limit=1)
                    if not lot_id:
                        lot_vals = {}
                        lot_vals['product_id'] = int(product_id)
                        lot_vals['name'] = str(data.get('lot_name', ''))
                        lot_id = self.env['stock.production.lot'].create(lot_vals)
                    vals = {}
                    vals['product_id'] = int(product_id)
                    vals['lot_id'] = lot_id.id
                    vals['qty'] = data.get('qty')
                    vals['user_id'] = self.env.user.id
                    vals['location_id'] = location_id
                    count_quant = self.env['stock.count.quant'].create(vals)
                    if (lot_id and lot_id.product_id.tracking == 'serial') and ('Product is already counted for Serial No.' in str(count_quant)):
                        return str(count_quant)
            return 'True'
        except:
            return 'False'

    def action_confirm(self):
        product_list = []
        if self.inventoried_product == 'all_products':
             product_list += [product_id.id for product_id in self.env['product.product'].search([])]
        else:
            if self.allow_other_category:
                product_list += [product_id.id for product_id in self.env['product.product'].search([('categ_id', '=', self.other_category.id)])]
            if self.inventoried_product == 'specific_category':
                product_list += [product_id.id for product_id in self.env['product.product'].search([('categ_id', '=', self.inventoried_category.id)])]
            elif self.inventoried_product == 'specific_product':
                product_list += [self.product_id.id]
        vals = {}
        vals['state'] = 'in_progress'
        vals['line_ids'] = [(0, 0, {'product_id': product_id}) for product_id in list(set(product_list))]
        self.write(vals)

    def action_done(self):
        self.action_inventory_adjustment()
        self.inv_id.action_done()
        self.write({'state': 'close'})

    def action_cancel(self):
        self.write({'state': 'cancel'})


    def action_inventory_adjustment(self):
        vals = {}
        vals['name'] = 'INV ADJUST: ' + self.name
        vals['filter'] = 'partial'
        vals['date'] = str(datetime.now())
        vals['location_id'] = self.location_id.id
        vals['company_id'] = self.env.user.company_id.id
        inv_id = self.env['stock.inventory'].create(vals)
        self.write({'inv_id': inv_id.id})
        inv_id.prepare_inventory()
        for line in self.line_ids:
            for quant in line.quant_ids:
                inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', quant.lot_id.id if quant.lot_id else False), ('inventory_id', '=', inv_id.id)])
                if not inv_line:
                    line_vals = {}
                    line_vals['product_id'] = line.product_id.id
                    line_vals['prod_lot_id'] = quant.lot_id.id if quant.lot_id else False
                    line_vals['product_qty'] = 0
                    line_vals['location_id'] = self.location_id.id
                    line_vals['inventory_id'] = inv_id.id
                    self.env['stock.inventory.line'].create(line_vals)
            for count_quant in line.count_lot_ids:
                inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', count_quant.lot_id.id if count_quant.lot_id else False), ('inventory_id', '=', inv_id.id)])
                if inv_line:
                    inv_line.write({'product_qty': inv_line.product_qty + count_quant.qty})
                else:
                    line_vals = {}
                    line_vals['product_id'] = line.product_id.id
                    line_vals['prod_lot_id'] = count_quant.lot_id.id if count_quant.lot_id else False
                    line_vals['product_qty'] = count_quant.qty
                    line_vals['location_id'] = self.location_id.id
                    line_vals['inventory_id'] = inv_id.id
                    self.env['stock.inventory.line'].create(line_vals)

StockCount()

class StockCountLine(models.Model):
    _name = 'stock.count.line'
    _description = 'Stock Count Lines'

    @api.depends('quant_ids', 'state', 'quant_ids.qty', 'quant_ids.lot_id')
    def compute_existing_qty(self):
        for record in self:
            record.existing_qty = sum([x.qty for x in record.quant_ids])

    # @api.depends('count_lot_ids', 'count_lot_ids.qty', 'count_lot_ids.lot_id')
    # def compute_count_qty(self):
    #     for record in self:
    #             record.count_qty = sum([x.qty for x in record.count_lot_ids])

    @api.depends('product_id', 'state')
    def _get_stock_quant(self):
        for record in self:
            if record.product_id:
                quant_ids = self.env['stock.quant'].search([('product_id', '=', record.product_id.id), ('location_id', '=', record.location_id.id)]).ids
            else:
                quant_ids = []
            record.quant_ids = [(6, 0, quant_ids)]

    count_id = fields.Many2one('stock.count', string='Stock Count')
    state = fields.Selection(related='count_id.state', copy=False, store=True, string='Status')
    location_id = fields.Many2one('stock.location', related='count_id.location_id', store=True, string='Location')
    product_id = fields.Many2one('product.product', required=True, string='Product')
    existing_qty = fields.Float(compute='compute_existing_qty', store=False, string='Existing Qty')
    quant_ids = fields.Many2many('stock.quant', compute='_get_stock_quant', string='Quants')
    count_qty = fields.Float(string='Count Quantity')
    count_lot_ids = fields.One2many('stock.count.quant', 'count_line_id', string='Lot/Serial Nos')
    tracking = fields.Selection(related='product_id.tracking', string='Tracking')

    @api.constrains('product_id', 'count_id')
    def _check_product(self):
        ids = self.env['stock.count.line'].search([('product_id', '=', self.product_id.id), ('count_id', '=', self.count_id.id)])
        if len(ids) > 1:
            raise ValidationError('Duplicate Products is not allowed.')

    def action_recount(self):
        for record in self:
            record.count_lot_ids.unlink()

    def find_lot_number(self, lot_name):
        self.ensure_one()
        lot_id = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id), ('name', '=', lot_name)], limit=1)
        if lot_id:
            vals = {}
            vals['lot_name'] = lot_id.name
            return vals
        else:
            return {}

    def view_existing_data(self):
        return {
            'name': 'Lot/Serial Numbers',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env['ir.model.data'].xmlid_to_res_id('ops_app_stock_take.stock_count_lot_form'),
            'res_model': 'stock.count.line',
            'target': 'new',
            'res_id': self.ids[0],
        }

    def view_count_data(self):
        if self.tracking == 'none':
            view_id = self.env['ir.model.data'].xmlid_to_res_id('ops_app_stock_take.stock_count_lot_form3')
        else:
            view_id = self.env['ir.model.data'].xmlid_to_res_id('ops_app_stock_take.stock_count_lot_form2')
        return {
            'name': 'Lot/Serial Numbers',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'stock.count.line',
            'target': 'new',
            'res_id': self.ids[0],
        }

    @api.multi
    def save(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
            if all(x.state == 'cancel' for x in record.count_id.line_ids):
                record.count_id.action_cancel()

StockCountLine()

class StockCountQuant(models.Model):
    _name = 'stock.count.quant'
    _description = 'Stock Count Quant'
    _rec_name = 'product_id'
    _order = 'id desc'

    count_line_id = fields.Many2one('stock.count.line', string='Count Line')
    product_id = fields.Many2one('product.product', required=True, string='Product')
    lot_id = fields.Many2one('stock.production.lot', required=False, string='Lot/Serial No')
    qty = fields.Float()
    # user_id = fields.Many2one('res.users', string='User')
    # location_id = fields.Many2one('stock.location', required=True, string='Location')

    # @api.model
    # def create(self, vals):
    #     record = super(StockCountQuant, self).create(vals)
    #     for line in self.env['stock.count.line'].search([('state', '=', 'in_progress'), ('location_id', '=', record.location_id.id), ('product_id', '=', record.product_id.id if record.product_id else False)]):
    #         line.write({'count_lot_ids': [(4, record.id)]})
    #         if line.product_id.tracking == 'serial':
    #             lot_ids = [x.lot_id for x in line.count_lot_ids]
    #             if len(lot_ids) != len(list(set(lot_ids))):
    #                 lot_ids.sort()
    #                 new_lot_ids = list(set(lot_ids))
    #                 duplicate_lot_ids = []
    #                 for i in range(len(new_lot_ids)):
    #                     if (lot_ids.count(new_lot_ids[i]) > 1):
    #                         duplicate_lot_ids.append(new_lot_ids[i])
    #                 record.unlink()
    #                 return 'Product is already counted for Serial No. '+ duplicate_lot_ids[0].name
    #     return record

StockCountQuant()