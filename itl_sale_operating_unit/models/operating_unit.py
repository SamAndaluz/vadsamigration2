from odoo import api, fields, models


class OperatingUnit(models.Model):

    _inherit = 'operating.unit'


    sequence = fields.Integer('sequence', help="Sequence for the handle.", default=10)