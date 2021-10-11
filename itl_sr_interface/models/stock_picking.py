from odoo import models, fields, api, _
from odoo.exceptions import UserError

from odoo.addons import decimal_precision as dp
from odoo.addons.delivery.models.stock_picking import StockPicking as Delivery_Stock_Picking

import logging
_logger = logging.getLogger(__name__)

class StockPickingCustom(models.Model):
    _inherit = 'stock.picking'


    def action_done(self):
        res = super(StockPickingCustom, self).action_done()

        if self.sale_id:
            activemq_message_id = self.env['activemq.message'].search([('sale_order_id','=',self.sale_id.id)])
            if activemq_message_id:
                for stock_line in self.move_ids_without_package:
                    if len(stock_line.move_line_ids) > 0:
                        serie_id = stock_line.move_line_ids[0].lot_id
                        sale_subscription_id = activemq_message_id.sale_subscription_id
                        if sale_subscription_id:
                            sale_subscription_id.iccid_number = serie_id.name
                            activemq_message_id.create_response_message(serie_id.name)
                            activemq_message_id.send_response_message_to_sr()
                            break

        return res