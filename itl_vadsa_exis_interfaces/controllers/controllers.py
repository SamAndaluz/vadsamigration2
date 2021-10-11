# -*- coding: utf-8 -*-
from odoo import http

# class ItlVadsaExisInterfaces(http.Controller):
#     @http.route('/itl_vadsa_exis_interfaces/itl_vadsa_exis_interfaces/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_vadsa_exis_interfaces/itl_vadsa_exis_interfaces/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_vadsa_exis_interfaces.listing', {
#             'root': '/itl_vadsa_exis_interfaces/itl_vadsa_exis_interfaces',
#             'objects': http.request.env['itl_vadsa_exis_interfaces.itl_vadsa_exis_interfaces'].search([]),
#         })

#     @http.route('/itl_vadsa_exis_interfaces/itl_vadsa_exis_interfaces/objects/<model("itl_vadsa_exis_interfaces.itl_vadsa_exis_interfaces"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_vadsa_exis_interfaces.object', {
#             'object': obj
#         })