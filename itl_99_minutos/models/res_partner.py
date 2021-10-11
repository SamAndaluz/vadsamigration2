from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    barcode_99minutos = fields.Char(string="Barcode", readonly=True, store=True)