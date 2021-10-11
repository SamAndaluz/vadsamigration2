from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

from odoo.addons.sale_operating_unit.models.sale_order import SaleOrder as sale_order


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    def _default_operating_unit(self):
        _logger.info("----------> new _default_operating_unit")
        #res = super(SaleOrderInherit, self)._default_operating_unit()
        _logger.info("----------> new _default_operating_unit")
        #team = self.env['crm.team']._get_default_team_id()
        #if team.operating_unit_id:
        #    return team.operating_unit_id
        return False
