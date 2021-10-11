
from odoo import _, api, fields, models

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('webpay_plus', 'WebPay Plus')])
    webpay_plus_company = fields.Char(string='Company', required_if_provider='webpay_plus', groups='base.group_user')
    webpay_plus_branch = fields.Char(string='Branch', required_if_provider='webpay_plus', groups='base.group_user')
    webpay_plus_data0 = fields.Char(string='Data0', required_if_provider='webpay_plus', groups='base.group_user')
    webpay_plus_key = fields.Char(string='Key', required_if_provider='webpay_plus', groups='base.group_user')
    webpay_plus_endpoint = fields.Char(string='URL Endpoint', required_if_provider='webpay_plus', groups='base.group_user')
    webpay_plus_user = fields.Char(string='User', required_if_provider='webpay_plus', groups='base.group_user')
    webpay_plus_pwd = fields.Char(string='Password', required_if_provider='webpay_plus', groups='base.group_user')
