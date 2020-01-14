# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import psycopg2
import psycopg2.extras

import logging
_logger = logging.getLogger(__name__)

class SyncSettings(models.Model):
    _name = 'sync.settings'
    _description = 'Sync Settings'
    _order = 'is_default, name ASC'

    name = fields.Char('Name', required=True, help='Connection Name')
    host = fields.Char('Host', required=True, help='IP address to connect')
    db_name = fields.Char('Database Name', required=True, help='Database Name')
    username = fields.Char('Username', required=True, help='Username')
    password = fields.Char('Password', help='Password')
    port = fields.Integer('Port', required=True, default=22)
    is_default = fields.Boolean('Is Default?', default=False, help='Is default connection')

    @api.multi
    def button_set_default(self):
        other_ids = self.search([('id','not in',self.ids)])
        other_ids.write({'is_default': False})
        self.write({'is_default': True})

    @api.multi
    def button_test(self):
        cr = False
        conn = False
        try:
            conn = psycopg2.connect(dbname=self.db_name, user=self.username, password=self.password, host=self.host, port=self.port)
            cr = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" # Just select all table names
            cr.execute(query)
            cr.fetchall()
        except Exception, e:
            raise UserError('Connection Failed!\n'+str(e))
        finally:
            try:
                cr.close()
                conn.close()
            except Exception:
                pass
        raise UserError('Connection Test Succeeded! Everything seems properly set up!')

    @api.multi
    def cron_process_import(self):
        config = self.search([('is_default', '=', True)])
        if config:
            cr = False
            conn = False
            try:
                conn = psycopg2.connect(dbname=config.db_name, user=config.username, password=config.password, host=config.host, port=config.port)
                cr = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                # res_partner import
                self.import_res_partner(cr, conn)
                # product_category import
                self.import_product_category(cr, conn)
                # product_uom import
                self.import_product_uom(cr, conn)
                # product_template import
                self.import_product_template(cr, conn)
                # stock_warehouse import
                self.import_stock_warehouse(cr, conn)
                # sale_order import
                self.import_sale_order(cr, conn)
                # purchase_order import
                self.import_purchase_order(cr, conn)
                # Stock Adjustment import
                self.import_stock_inventory(cr, conn)
                # internal transfer import
                self.import_internal_transfer(cr, conn)
            except Exception, e:
                _logger.error('\nPowerone sync Error: %s\n' % str(e))
            finally:
                try:
                    cr.close()
                    conn.close()
                except Exception:
                    pass
        return True

    @api.multi
    def import_res_partner(self, cr, conn):
        # Process columns
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='res_partner';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM res_partner WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            vals = {}
            vals['company_type'] = 'company'
            vals['name'] = line[columns.index('name')]
            vals['active'] = line[columns.index('active')]
            vals['street'] = line[columns.index('street')]
            vals['street2'] = line[columns.index('street2')]
            vals['city'] = line[columns.index('city')]
            country_id = self.env['res.country'].search([('name', 'ilike', line[columns.index('country_id')])], limit=1)
            if not country_id:
                country_id = self.env['res.country'].create({'name': line[columns.index('country_id')]})
            vals['country_id'] = country_id.id
            state_id = self.env['res.country.state'].search([('name','ilike',line[columns.index('state_id')])], limit=1)
            if not state_id:
                state_id = self.env['res.country.state'].create({'name': line[columns.index('state_id')], 'country_id': country_id.id, 'code': '00'})
            vals['state_id'] = state_id.id
            vals['zip'] = line[columns.index('zip')]
            vals['email'] = line[columns.index('email')]
            vals['phone'] = line[columns.index('phone')]
            vals['mobile'] = line[columns.index('mobile')]
            vals['fax'] = line[columns.index('fax')]
            vals['supplier'] = line[columns.index('supplier')]
            vals['customer'] = line[columns.index('customer')]
            vals['type'] = line[columns.index('type')]
            vals['credit_limit'] = line[columns.index('credit_limit')]
            vals['debit_limit'] = line[columns.index('debit_limit')]
            vals['user_id'] = line[columns.index('user_id')]
            # vals['status'] = line[columns.index('status')]
            # Create partner in odoo
            partner = self.env['res.partner'].create(vals)
            # Update powerone table
            query = 'UPDATE res_partner SET odoo_id=%s WHERE id=%s;' % (partner.id, line[columns.index('id')])
            cr.execute(query)
            conn.commit()
        return True

    @api.multi
    def import_product_category(self, cr, conn):
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='product_category';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM product_category WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            vals = {}
            vals['name'] = line[columns.index('name')]
            if line[columns.index('parent_id')]:
                parent_id = self.env['product.category'].search([('name', '=', line[columns.index('parent_id')])], limit=1)
                if not parent_id:
                    parent_id = self.env['product.category'].create({'name': line[columns.index('parent_id')]})
                vals['parent_id'] = parent_id.id
            # Create product_category in odoo
            product_category = self.env['product.category'].create(vals)
            # Update powerone table
            query = 'UPDATE product_category SET odoo_id=%s WHERE id=%s;' % (product_category.id, line[columns.index('id')])
            cr.execute(query)
            conn.commit()
        return True

    @api.multi
    def import_product_uom(self, cr, conn):
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='product_uom';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM product_uom WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            vals = {}
            vals['name'] = line[columns.index('name')]
            vals['factor'] = 100.000
            vals['uom_type'] = 'reference'
            vals['rounding'] = line[columns.index('rounding')]
            if line[columns.index('category_id')]:
                category_id = self.env['product.uom.categ'].search([('name', '=', line[columns.index('category_id')])],limit=1)
                if not category_id:
                    category_id = self.env['product.uom.categ'].create({'name': line[columns.index('category_id')]})
                vals['category_id'] = category_id.id
            # Create product_uom in odoo
            product_uom = self.env['product.uom'].create(vals)
            # Update powerone table
            query = 'UPDATE product_uom SET odoo_id=%s WHERE id=%s;' % (product_uom.id, line[columns.index('id')])
            cr.execute(query)
            conn.commit()
        return True

    @api.multi
    def import_product_template(self, cr, conn):
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='product_template';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM product_template WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            vals = {}
            vals['name'] = line[columns.index('name')]
            vals['type'] = 'product'
            if line[columns.index('categ_id')]:
                categ_id = self.env['product.category'].search([('name', '=', line[columns.index('categ_id')])], limit=1)
                if not categ_id:
                    categ_id = self.env['product.category'].create({'name': line[columns.index('categ_id')]})
                vals['categ_id'] = categ_id.id
            vals['default_code'] = line[columns.index('default_code')]
            vals['list_price'] = line[columns.index('list_price')]
            vals['standard_price'] = line[columns.index('standard_price')]
            # vals['brand_id'] = 3
            if line[columns.index('uom_id')]:
                uom_id = self.env['product.uom'].search([('name', 'ilike', line[columns.index('uom_id')])],limit=1)
                if not uom_id:
                    uom_id = self.env['product.uom'].create({'name': line[columns.index('uom_id')]})
                vals['uom_id'] = uom_id.id
            # Create product_template in odoo
            product_template = self.env['product.template'].create(vals)
            # Update powerone table
            query = 'UPDATE product_template SET odoo_id=%s WHERE id=%s;' % (product_template.id, line[columns.index('id')])
            cr.execute(query)
            conn.commit()
        return True

    @api.multi
    def import_stock_warehouse(self, cr, conn):
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='stock_warehouse';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM stock_warehouse WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            warehouse_id = self.env['stock.warehouse'].search([('code','=',line[columns.index('code')])])
            if not warehouse_id:
                vals = {}
                vals['name'] = line[columns.index('name')]
                vals['code'] = line[columns.index('code')]
                # Create warehouse in odoo
                warehouse = self.env['stock.warehouse'].create(vals)
                # Update powerone table
                query = 'UPDATE stock_warehouse SET odoo_id=%s WHERE id=%s;' % (warehouse.id, line[columns.index('id')])
                cr.execute(query)
                conn.commit()
        return True

    @api.multi
    def import_sale_order(self, cr, conn):
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='sale_order';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM sale_order WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            vals = {}
            vals['name'] = line[columns.index('name')]
            vals['state'] = 'draft'
            vals['date_order'] = line[columns.index('date_order')]
            if line[columns.index('partner_id')]:
                partner_id = self.env['res.partner'].search([('name', '=', line[columns.index('partner_id')])], limit=1)
                if not partner_id:
                    partner_id = self.env['res.partner'].create({'name': line[columns.index('partner_id')]})
                vals['partner_id'] = partner_id.id
            if line[columns.index('pricelist_id')]:
                pricelist_id = self.env['product.pricelist'].search([('name', '=', line[columns.index('pricelist_id')])], limit=1)
                if not pricelist_id:
                    pricelist_id = self.env['product.pricelist'].create({'name': line[columns.index('pricelist_id')]})
                vals['pricelist_id'] = pricelist_id.id
            if line[columns.index('payment_term_id')]:
                payment_term_id = self.env['account.payment.term'].search([('name', '=', line[columns.index('payment_term_id')])], limit=1)
                if not payment_term_id:
                    payment_term_id = self.env['account.payment.term'].create({'name': line[columns.index('payment_term_id')]})
                vals['payment_term_id'] = payment_term_id.id
            if line[columns.index('team_id')]:
                team_id = self.env['crm.team'].search([('name', '=', line[columns.index('team_id')])], limit=1)
                if not team_id:
                    team_id = self.env['crm.team'].create({'name': line[columns.index('team_id')]})
                vals['team_id'] = team_id.id
            if line[columns.index('user_id')]:
                user_id = self.env['res.users'].search([('name', '=', line[columns.index('user_id')])], limit=1)
                if not user_id:
                    user_id = self.env['res.users'].create({'name': line[columns.index('user_id')]})
                vals['user_id'] = user_id.id
            # Create sale_order in odoo
            sale_order = self.env['sale.order'].create(vals)

            order_line_vals = {}
            categ_id = self.env['product.category'].search([('name', '=', 'All')], limit=1)
            if line[columns.index('product_id')]:
                product_id = self.env['product.product'].search([('name', 'ilike', line[columns.index('product_id')])], limit=1)
                if not product_id:
                    product_id = self.env['product.product'].create({'name': line[columns.index('product_id')], 'categ_id': categ_id.id, 'brand_id': 3})
                order_line_vals['product_id'] = product_id.id
            order_line_vals['product_uom_qty'] = line[columns.index('product_uom_qty')]
            order_line_vals['price_unit'] = line[columns.index('price_unit')]
            order_line_vals['name'] = line[columns.index('order_line_description')]
            order_line_vals['discount'] = line[columns.index('discount')]
            order_line_vals['order_id'] = sale_order.id
            if line[columns.index('product_uom')]:
                product_uom = self.env['product.uom'].search([('name', '=', line[columns.index('product_uom')])], limit=1)
                if not product_uom:
                    product_uom = self.env['product.uom'].create({'name': line[columns.index('product_uom')]})
                order_line_vals['product_uom'] = product_uom.id

            # Create sale_order_line in odoo
            sale_order_line = self.env['sale.order.line'].create(order_line_vals)
            # Update powerone table
            query = 'UPDATE sale_order SET odoo_id=%s WHERE id=%s;' % (sale_order.id, line[columns.index('id')])
            cr.execute(query)
            conn.commit()
            sale_order.write({'state': 'sale'})
            sale_order.action_invoice_create(final=True)
        return True

    @api.multi
    def import_purchase_order(self, cr, conn):
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='purchase_order';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM purchase_order WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            vals = {}
            if line[columns.index('name')]:
                vals['name'] = line[columns.index('name')]
            else:
                vals['name'] = ' '
            vals['state'] = 'purchase'
            vals['date_order'] = line[columns.index('date_order')]
            vals['date_planned'] = line[columns.index('date_planned')]
            vals['notes'] = line[columns.index('notes')]
            if line[columns.index('partner_id')]:
                partner_id = self.env['res.partner'].search([('name', '=', line[columns.index('partner_id')])], limit=1)
                if not partner_id:
                    partner_id = self.env['res.partner'].create({'name': line[columns.index('partner_id')]})
                vals['partner_id'] = partner_id.id
            # Create purchase_order in odoo
            purchase_order = self.env['purchase.order'].create(vals)

            order_line_vals = {}
            if line[columns.index('product_id')]:
                product_id = self.env['product.product'].search([('name', 'ilike', line[columns.index('product_id')])], limit=1)
                if not product_id:
                    product_id = self.env['product.product'].create({'name': line[columns.index('product_id')], 'categ_id': 81})
                order_line_vals['product_id'] = product_id.id
            order_line_vals['product_qty'] = line[columns.index('product_qty')]
            order_line_vals['price_unit'] = line[columns.index('price_unit')]
            order_line_vals['name'] = line[columns.index('order_line_description')]
            order_line_vals['date_planned'] = line[columns.index('date_planned')]
            order_line_vals['order_id'] = purchase_order.id
            if line[columns.index('product_uom')]:
                product_uom = self.env['product.uom'].search([('name', '=', line[columns.index('product_uom')])], limit=1)
                if not product_uom:
                    product_uom = self.env['product.uom'].create({'name': line[columns.index('product_uom')]})
                order_line_vals['product_uom'] = product_uom.id

            # Create purchase_order_line in odoo
            purchase_order_line = self.env['purchase.order.line'].create(order_line_vals)
            # Update powerone table
            query = 'UPDATE purchase_order SET odoo_id=%s WHERE id=%s;' % (purchase_order.id, line[columns.index('id')])
            cr.execute(query)
            conn.commit()
        return True

    @api.multi
    def import_stock_inventory(self, cr, conn):
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='stock_inventory';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM stock_inventory WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            vals = {}
            vals['name'] = line[columns.index('name')]
            if line[columns.index('location_id')]:
                location_id = self.env['stock.location'].search([('name', 'ilike', line[columns.index('location_id')])], limit=1)
                if not location_id:
                    location_id = self.env['stock.location'].create({'name': line[columns.index('location_id')], 'usage': 'internal'})
                vals['location_id'] = location_id.id
            vals['date'] = line[columns.index('date')]
            vals['filter'] = line[columns.index('filter')] or 'none'
            # if line[columns.index('partner_id')]:
            #     partner_id = self.env['res.partner'].search([('name', '=', line[columns.index('partner_id')])], limit=1)
            #     if not partner_id:
            #         partner_id = self.env['res.partner'].create({'name': line[columns.index('partner_id')]})
            #     vals['partner_id'] = partner_id.id
            vals['state'] = line[columns.index('state')]
            # Create stock_inventory in odoo
            stock_inventory = self.env['stock.inventory'].create(vals)

            order_line_vals = {}
            if line[columns.index('product_id')]:
                product_id = self.env['product.product'].search([('name', 'ilike', line[columns.index('product_id')])],limit=1)
                if not product_id:
                    product_id = self.env['product.product'].create({'name': line[columns.index('product_id')], 'categ_id': 81})
                order_line_vals['product_id'] = product_id.id
                order_line_vals['product_uom_id'] = product_id.uom_id.id
            order_line_vals['inventory_id'] = stock_inventory.id
            location_id = self.env['stock.location'].search([('name', '=', 'Stock')], limit=1)
            if location_id:
                order_line_vals['location_id'] = location_id.id

            # Create stock_inventory_line in odoo
            self.env['stock.inventory.line'].create(order_line_vals)
            # Update powerone table
            query = 'UPDATE stock_inventory SET odoo_id=%s WHERE id=%s;' % (stock_inventory.id, line[columns.index('id')])
            cr.execute(query)
            conn.commit()
        return True

    @api.multi
    def import_internal_transfer(self, cr, conn):
        query = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='internal_transfer';"
        cr.execute(query)
        columns = map(lambda x: x[0], cr.fetchall())
        # Process data
        query = "SELECT * FROM internal_transfer WHERE odoo_id is NULL;"
        cr.execute(query)
        for line in cr.fetchall():
            vals = {}
            vals['name'] = line[columns.index('name')]
            vals['schedule_date'] = fields.Datetime.now()
            if line[columns.index('source_loc_id')]:
                source_loc_id = self.env['stock.location'].search([('name', 'ilike', line[columns.index('source_loc_id')])],limit=1)
                if not source_loc_id:
                    source_loc_id = self.env['stock.location'].create({'name': line[columns.index('source_loc_id')], 'usage': 'internal'})
                vals['source_loc_id'] = source_loc_id.id
            if line[columns.index('dest_loc_id')]:
                dest_loc_id = self.env['stock.location'].search([('name', 'ilike', line[columns.index('dest_loc_id')])],limit=1)
                if not dest_loc_id:
                    dest_loc_id = self.env['stock.location'].create({'name': line[columns.index('dest_loc_id')], 'usage': 'internal'})
                vals['dest_loc_id'] = dest_loc_id.id

            if line[columns.index('picking_type_outgoing_id')]:
                picking_type_outgoing_id = self.env['stock.picking.type'].search([('name', '=', line[columns.index('picking_type_outgoing_id')])],limit=1)
                if not picking_type_outgoing_id:
                    picking_type_outgoing_id = self.env['stock.picking.type'].create({'name': line[columns.index('picking_type_outgoing_id')]})
                vals['picking_type_outgoing_id'] = picking_type_outgoing_id.id
            if line[columns.index('picking_type_incoming_id')]:
                picking_type_incoming_id = self.env['stock.picking.type'].search([('name', '=', line[columns.index('picking_type_incoming_id')])], limit=1)
                if not picking_type_incoming_id:
                    picking_type_outgoing_id = self.env['stock.picking.type'].create({'name': line[columns.index('picking_type_incoming_id')]})
                vals['picking_type_incoming_id'] = picking_type_incoming_id.id
            vals['state'] = 'draft'
            # Create internal_transfer in odoo
            internal_transfer = self.env['internal.transfer'].create(vals)

            order_line_vals = {}
            if line[columns.index('product_id')]:
                product_id = self.env['product.product'].search([('name', 'ilike', line[columns.index('product_id')])],limit=1)
                if not product_id:
                    product_id = self.env['product.product'].create({'name': line[columns.index('product_id')], 'categ_id': 81})
                order_line_vals['product_id'] = product_id.id
                order_line_vals['uom_id'] = product_id.uom_id.id
            order_line_vals['product_uom_qty'] = line[columns.index('product_uom_qty')]
            order_line_vals['transfer_id'] = internal_transfer.id
            # Create stock_inventory_line in odoo
            self.env['internal.transfer.line'].create(order_line_vals)
            # Update powerone table
            query = 'UPDATE internal_transfer SET odoo_id=%s WHERE id=%s;' % (internal_transfer.id, line[columns.index('id')])
            cr.execute(query)
            conn.commit()
            internal_transfer.button_confirm()
        return True

SyncSettings()