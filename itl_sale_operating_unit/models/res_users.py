# Copyright 2015-TODAY Eficent
# - Jordi Ballester Alomar
# Copyright 2015-TODAY Serpent Consulting Services Pvt. Ltd. - Sudhir Arya
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):

    _inherit = 'res.users'

    @api.model
    def operating_unit_default_get(self, uid2=False):
        if not uid2:
            uid2 = self._uid
        user = self.env['res.users'].browse(uid2)
        return user.default_operating_unit_id

    @api.model
    def _default_operating_unit(self):
        return self.operating_unit_default_get()

    @api.model
    def _default_operating_units(self):
        return self._default_operating_unit()

    operating_unit_ids = fields.Many2many(
        'operating.unit', 'operating_unit_users_rel', 'user_id', 'poid',
        'Operating Units', default=lambda self: self._default_operating_units()
    )
    default_operating_unit_id = fields.Many2one(
        'operating.unit', 'Default Operating Unit',
        compute="_default_operating_unit2"
    )

    @api.depends('operating_unit_ids')
    def _default_operating_unit2(self, uid2=False):
        if not uid2:
            if len(self.ids) == 0:
                uid2 = self.id
            if len(self.ids) != 0:
                uid2 = self.ids[0]
            if not uid2 and "params" in self._context:
                uid2 = self._context["params"]["id"]
        #_logger.info("--> uid2: " + str(uid2))
        user = self.env['res.users'].browse(uid2)
        if not user:
            return
        _logger.info("--> user.company_id: " + str(user.company_id))
        user.default_operating_unit_id = False
        if len(user.operating_unit_ids) > 0:
            op_unit_filtered = user.operating_unit_ids.filtered(lambda op_unit: op_unit.company_id == user.company_id).sorted(key=lambda r: r.sequence)
            if len(op_unit_filtered) > 0:
                user.default_operating_unit_id = user.operating_unit_ids.filtered(lambda op_unit: op_unit.company_id == user.company_id).sorted(key=lambda r: r.sequence)[0]
    
    def _get_default_operating_unit(self, uid2=False):
        user = self
        operating_unit_ids = user.operating_unit_ids.filtered(lambda op_unit: op_unit.company_id == user.company_id)
        _logger.info("---> _get_default_operating_unit: " + str(operating_unit_ids))
        if len(operating_unit_ids) > 0:
            return operating_unit_ids.sorted(key=lambda r: r.sequence)[0].id
        else:
            return False
    