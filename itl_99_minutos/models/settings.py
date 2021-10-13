
from odoo import models, fields, api
import ast

import logging
_logger = logging.getLogger(__name__)

class _99MinutosSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    @api.model
    def _get_delivery_address_domain(self):
        _logger.info("---> self.env.user.company_id.partner_id: " + str(self.env.user.company_id.partner_id))
        _logger.info("---> self.env.user.company_id: " + str(self.env.user.company_id))
        return [('type','=','delivery')]

    delivery_address_99_minutos = fields.Many2one('res.partner', string="Delivery address", domain=_get_delivery_address_domain, readonly=False)
    
    email_from_99minutos = fields.Char(string="Email from", help="Correo electrónico del remitente de notificaciones de no cobertura.", readonly=False)
    email_to_99minutos = fields.Char(string="Email to", help="Correo electrónico del destinatario de notificaciones de no cobertura.", readonly=False)
    res_partner_ids_notification_99minutos = fields.Many2many('res.partner', string="Contactos para notificación", help="Contactos para notificación de no cobertura", readonly=False)
    url_tracking_99minutos = fields.Char(string="URL for tracking", help="URL que se enviará por correo para el seguimiento del envío.", readonly=False)
    email_from_tracking_99minutos = fields.Char(string="Email from - for Tracking", help="Si está configurado lo pone como correo del destinatario, si no usa el del sistema.", readonly=False)
    user_send_email_99minutos = fields.Many2one('res.users', string="User for sending email tracking notification", help="Si está configurado lo usa como el usuario que envía el correo de tracking.", readonly=False)


    @api.model
    def get_values(self):
        res = super(_99MinutosSettings, self).get_values()
        res_partner_ids_notification_99minutos = self.env['ir.config_parameter'].sudo().get_param('itl_99_minutos.res_partner_ids_notification_99minutos')
        if res_partner_ids_notification_99minutos:
            res.update(res_partner_ids_notification_99minutos = [(6, 0, ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param('itl_99_minutos.res_partner_ids_notification_99minutos')))])
        res.update(
            delivery_address_99_minutos = int(self.env['ir.config_parameter'].sudo().get_param('itl_99_minutos.delivery_address_99_minutos')),
            email_from_99minutos = self.env['ir.config_parameter'].sudo().get_param('itl_99_minutos.email_from_99minutos'),
            email_to_99minutos = self.env['ir.config_parameter'].sudo().get_param('itl_99_minutos.email_to_99minutos'),
            url_tracking_99minutos = self.env['ir.config_parameter'].sudo().get_param('itl_99_minutos.url_tracking_99minutos'),
            email_from_tracking_99minutos = self.env['ir.config_parameter'].sudo().get_param('itl_99_minutos.email_from_tracking_99minutos'),
            user_send_email_99minutos = int(self.env['ir.config_parameter'].sudo().get_param('itl_99_minutos.user_send_email_99minutos'))
        )
        return res

    
    def set_values(self):
        super(_99MinutosSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()

        delivery_address_99_minutos = self.delivery_address_99_minutos and self.delivery_address_99_minutos.id or False
        email_from_99minutos = self.email_from_99minutos or False
        email_to_99minutos = self.email_to_99minutos or False
        url_tracking_99minutos = self.url_tracking_99minutos or False
        email_from_tracking_99minutos = self.email_from_tracking_99minutos or False
        user_send_email_99minutos = self.user_send_email_99minutos and self.user_send_email_99minutos.id or False
        res_partner_ids_notification_99minutos = self.res_partner_ids_notification_99minutos and self.res_partner_ids_notification_99minutos.ids or False

        param.set_param('itl_99_minutos.delivery_address_99_minutos', delivery_address_99_minutos)
        param.set_param('itl_99_minutos.email_from_99minutos', email_from_99minutos)
        param.set_param('itl_99_minutos.email_to_99minutos', email_to_99minutos)
        param.set_param('itl_99_minutos.url_tracking_99minutos', url_tracking_99minutos)
        param.set_param('itl_99_minutos.email_from_tracking_99minutos', email_from_tracking_99minutos)
        param.set_param('itl_99_minutos.user_send_email_99minutos', user_send_email_99minutos)
        param.set_param('itl_99_minutos.res_partner_ids_notification_99minutos', res_partner_ids_notification_99minutos)
