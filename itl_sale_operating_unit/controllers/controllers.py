# -*- coding: utf-8 -*-
from odoo import http

# class ItlSaleOperatingUnit(http.Controller):
#     @http.route('/itl_sale_operating_unit/itl_sale_operating_unit/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_sale_operating_unit/itl_sale_operating_unit/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_sale_operating_unit.listing', {
#             'root': '/itl_sale_operating_unit/itl_sale_operating_unit',
#             'objects': http.request.env['itl_sale_operating_unit.itl_sale_operating_unit'].search([]),
#         })

#     @http.route('/itl_sale_operating_unit/itl_sale_operating_unit/objects/<model("itl_sale_operating_unit.itl_sale_operating_unit"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_sale_operating_unit.object', {
#             'object': obj
#         })