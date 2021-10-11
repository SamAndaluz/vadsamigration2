from odoo import _, api, fields, models

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    stripe_current_host = fields.Char(string='Current host', required_if_provider='stripe', groups='base.group_user')