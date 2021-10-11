# -*- coding: utf-8 -*-
from odoo import http

# class ItlL10nMxEdi(http.Controller):
#     @http.route('/itl_l10n_mx_edi/itl_l10n_mx_edi/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_l10n_mx_edi/itl_l10n_mx_edi/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_l10n_mx_edi.listing', {
#             'root': '/itl_l10n_mx_edi/itl_l10n_mx_edi',
#             'objects': http.request.env['itl_l10n_mx_edi.itl_l10n_mx_edi'].search([]),
#         })

#     @http.route('/itl_l10n_mx_edi/itl_l10n_mx_edi/objects/<model("itl_l10n_mx_edi.itl_l10n_mx_edi"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_l10n_mx_edi.object', {
#             'object': obj
#         })