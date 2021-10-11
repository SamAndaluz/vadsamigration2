# -*- coding: utf-8 -*-
from odoo import http

# class ItlSerialNumberPo(http.Controller):
#     @http.route('/itl_serial_number_po/itl_serial_number_po/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_serial_number_po/itl_serial_number_po/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_serial_number_po.listing', {
#             'root': '/itl_serial_number_po/itl_serial_number_po',
#             'objects': http.request.env['itl_serial_number_po.itl_serial_number_po'].search([]),
#         })

#     @http.route('/itl_serial_number_po/itl_serial_number_po/objects/<model("itl_serial_number_po.itl_serial_number_po"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_serial_number_po.object', {
#             'object': obj
#         })