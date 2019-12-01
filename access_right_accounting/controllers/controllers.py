# -*- coding: utf-8 -*-
from odoo import http

# class AccessRightAccounting(http.Controller):
#     @http.route('/access_right_accounting/access_right_accounting/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/access_right_accounting/access_right_accounting/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('access_right_accounting.listing', {
#             'root': '/access_right_accounting/access_right_accounting',
#             'objects': http.request.env['access_right_accounting.access_right_accounting'].search([]),
#         })

#     @http.route('/access_right_accounting/access_right_accounting/objects/<model("access_right_accounting.access_right_accounting"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('access_right_accounting.object', {
#             'object': obj
#         })