from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    
    #@api.model
    #def _get_delivery_address_domain(self):
    #    return [('parent_id', '=', self.env.user.company_id.partner_id.id),('company_id','=',self.env.user.company_id.id),('type','=','delivery')]

    #delivery_address_99_minutos = fields.Many2one('res.partner', string="Delivery address", domain=_get_delivery_address_domain)
    
    #email_from_99minutos = fields.Char(string="Email from")
    #email_to_99minutos = fields.Char(string="Email to")
    #url_tracking_99minutos = fields.Char(string="URL for tracking")
    #email_from_tracking_99minutos = fields.Char(string="Email from - for Tracking")
    #user_send_email_99minutos = fields.Many2one('res.users', string="User for sending email notification")