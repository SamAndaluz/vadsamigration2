# -*- coding: utf-8 -*-
from odoo import http

# class ItlElavonCron(http.Controller):
#     @http.route('/itl_elavon_cron/itl_elavon_cron/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itl_elavon_cron/itl_elavon_cron/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('itl_elavon_cron.listing', {
#             'root': '/itl_elavon_cron/itl_elavon_cron',
#             'objects': http.request.env['itl_elavon_cron.itl_elavon_cron'].search([]),
#         })

#     @http.route('/itl_elavon_cron/itl_elavon_cron/objects/<model("itl_elavon_cron.itl_elavon_cron"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itl_elavon_cron.object', {
#             'object': obj
#         })