# -*- coding: utf-8 -*-
from odoo import http

import logging
_logger = logging.getLogger(__name__)

class Itl99Minutos(http.Controller):
    
    @http.route(['/odoo/99minutos/notifications'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def index(self, **post):
        payload = http.request.jsonrequest
        _logger.info("response: %s", payload)
        param = http.request.env['ir.config_parameter'].sudo()
        user = param.get_param('itl_99_minutos.user_send_email_99minutos')
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id') or False
        user_id = http.request.env['res.users'].sudo().browse(int(user))
        response = http.request.env['itl.99.minutos.notification'].sudo().create({'response': str(payload), 'company_id': sr_company_id})

        response.with_context(force_company=sr_company_id).sudo().save_barcode()