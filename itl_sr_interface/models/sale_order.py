from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class SaleOrderInherit(models.Model):
    _inherit = "sale.order"


    update_delivery_method = fields.Boolean(default=False, copy=False)
    

    def set_update_delivery_method(self):
    	if self.update_delivery_method:
    		self.update_delivery_method = False
    	else:
    		self.update_delivery_method = True

    def get_delivery_price(self):
    	# Inherit method
    	# Allow SO in sale state
        for order in self.filtered(lambda o: o.state in ('draft', 'sent', 'sale') and len(o.order_line) > 0):
            # We do not want to recompute the shipping price of an already validated/done SO
            # or on an SO that has no lines yet
            order.delivery_rating_success = False
            res = order.carrier_id.rate_shipment(order)
            if res['success']:
                order.delivery_rating_success = True
                order.delivery_price = res['price']
                order.delivery_message = res['warning_message']
            else:
                order.delivery_rating_success = False
                order.delivery_price = 0.0
                order.delivery_message = res['error_message']
