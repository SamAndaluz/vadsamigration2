# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero

import logging
_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    
    @api.constrains('quantity')
    def check_quantity(self):
        for quant in self:
            if float_compare(quant.quantity, 1, precision_rounding=quant.product_uom_id.rounding) > 0 and quant.lot_id and quant.product_id.tracking == 'serial' and quant.company_id == self.env.user.company_id:
                message_base = _('A serial number should only be linked to a single product.')
                message_quant = _('Please check the following serial number (name, id): ')
                message_sn = '(%s, %s)' % (quant.lot_id.name, quant.lot_id.id)
                raise ValidationError("\n".join([message_base, message_quant, message_sn]))