# -*- coding: utf-8 -*-
from odoo import http

# class ItlCmpInterface(http.Controller):
#     @http.route('/itl_cmp_interface/itl_cmp_interface/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_cmp_interface/itl_cmp_interface/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_cmp_interface.listing', {
#             'root': '/itl_cmp_interface/itl_cmp_interface',
#             'objects': http.request.env['itl_cmp_interface.itl_cmp_interface'].search([]),
#         })

#     @http.route('/itl_cmp_interface/itl_cmp_interface/objects/<model("itl_cmp_interface.itl_cmp_interface"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_cmp_interface.object', {
#             'object': obj
#         })