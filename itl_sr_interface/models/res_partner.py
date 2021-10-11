
from odoo import api, fields, models, _

import re

class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_id_ref = fields.Char(string='Customer Ref')
    token_ids = fields.One2many('res.partner.token', 'partner_id', string="Tokens")
    vat_invalid = fields.Char(string="VAT error", readonly=True, store=True)
    itl_state = fields.Char(string="Estado")

    def validate_rfc(self, rfc):
        pattern = re.compile("^([A-ZÑ&]{3,4}) ?(?:- ?)?(\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])) ?(?:- ?)?([A-Z\d]{2})([A\d])$")

        return True if pattern.match(rfc) != None else False

class ResPartnerToken(models.Model):
    _name = "res.partner.token"

    cardToken = fields.Char(string="Card token")
    reservedMsisdn = fields.Char(string="Reserved Msisdn")
    cardType = fields.Char(tring="Card type")
    partner_id = fields.Many2one('res.partner', ondelete='cascade')

    