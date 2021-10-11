from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    token_wpp_ids = fields.One2many('res.partner.token.wpp', 'partner_id', string="Tokens WPP")


class ResPartnerToken(models.Model):
    _name = "res.partner.token.wpp"

    cardToken = fields.Char(string="Card token")
    #cardType = fields.Selection([('visa', 'Visa'),('mastercard','Mastercard'),('american_express','American Express')], string="Card type")
    partner_id = fields.Many2one('res.partner', ondelete='cascade')