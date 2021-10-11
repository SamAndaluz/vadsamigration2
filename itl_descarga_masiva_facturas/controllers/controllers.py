# -*- coding: utf-8 -*-
# from odoo import http


# class ItlDescargaMasivaFacturas(http.Controller):
#     @http.route('/itl_descarga_masiva_facturas/itl_descarga_masiva_facturas/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_descarga_masiva_facturas/itl_descarga_masiva_facturas/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_descarga_masiva_facturas.listing', {
#             'root': '/itl_descarga_masiva_facturas/itl_descarga_masiva_facturas',
#             'objects': http.request.env['itl_descarga_masiva_facturas.itl_descarga_masiva_facturas'].search([]),
#         })

#     @http.route('/itl_descarga_masiva_facturas/itl_descarga_masiva_facturas/objects/<model("itl_descarga_masiva_facturas.itl_descarga_masiva_facturas"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_descarga_masiva_facturas.object', {
#             'object': obj
#         })
