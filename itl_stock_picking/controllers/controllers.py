# -*- coding: utf-8 -*-
from odoo import http

# class ItlStockPicking(http.Controller):
#     @http.route('/itl_stock_picking/itl_stock_picking/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_stock_picking/itl_stock_picking/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_stock_picking.listing', {
#             'root': '/itl_stock_picking/itl_stock_picking',
#             'objects': http.request.env['itl_stock_picking.itl_stock_picking'].search([]),
#         })

#     @http.route('/itl_stock_picking/itl_stock_picking/objects/<model("itl_stock_picking.itl_stock_picking"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_stock_picking.object', {
#             'object': obj
#         })