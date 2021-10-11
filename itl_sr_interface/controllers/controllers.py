# -*- coding: utf-8 -*-
from odoo import http

# class ItlSrInterface(http.Controller):
#     @http.route('/itl_sr_interface/itl_sr_interface/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_sr_interface/itl_sr_interface/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_sr_interface.listing', {
#             'root': '/itl_sr_interface/itl_sr_interface',
#             'objects': http.request.env['itl_sr_interface.itl_sr_interface'].search([]),
#         })

#     @http.route('/itl_sr_interface/itl_sr_interface/objects/<model("itl_sr_interface.itl_sr_interface"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_sr_interface.object', {
#             'object': obj
#         })