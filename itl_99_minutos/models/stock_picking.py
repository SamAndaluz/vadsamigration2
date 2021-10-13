from odoo import models, fields, api, _
from odoo.exceptions import UserError

from odoo.addons import decimal_precision as dp
from odoo.addons.delivery.models.stock_picking import StockPicking as Delivery_Stock_Picking

import logging
_logger = logging.getLogger(__name__)



################ Override a inherit method #############
def action_done(self):
    res = super(Delivery_Stock_Picking, self).action_done()
    for pick in self:
        if pick.carrier_id:
            if pick.carrier_id.integration_level == 'rate_and_ship':
                #_logger.info("-> pick.carrier_delivery_type: " + str(pick.carrier_delivery_type))
                if pick.carrier_delivery_type != '_99minutos':
                    pick.send_to_shipper()
            pick._add_delivery_cost_to_so()
    #raise UserError("Testing...")
    return res

Delivery_Stock_Picking.action_done = action_done
########################################################


class StockPickingCustom(models.Model):
    _inherit = 'stock.picking'
    
    carrier_counter_ref = fields.Char(string='Counter Reference', copy=False)
    carrier_delivery_type = fields.Selection(related="carrier_id.delivery_type", readonly=True)
    #state = fields.Selection(selection_add=[('send_to_99minutos','Enviado a 99minutos')])
    
    @api.model
    def create(self, vals):
        record = super(StockPickingCustom, self).create(vals)
        
        if record.carrier_delivery_type == '_99minutos':
            record.send_to_shipper()
        
        return record


    def send_to_shipper(self):
        self.ensure_one()
        res = self.carrier_id.send_shipping(self)
        if res:
            res = res[0]
            if self.carrier_id.free_over and self.sale_id and self.sale_id._compute_amount_total_without_delivery() >= self.carrier_id.amount:
                res['exact_price'] = 0.0
            self.carrier_price = res['exact_price']
            if res['tracking_number']:
                self.carrier_tracking_ref = res['tracking_number']
            # For 99 minutos
            if 'counter_number' in res and res['counter_number']:
                self.carrier_counter_ref = res['counter_number']
            order_currency = self.sale_id.currency_id or self.company_id.currency_id
            msg = _("Shipment sent to carrier %s for shipping with tracking number %s and counter number %s") % (self.carrier_id.name, self.carrier_tracking_ref, self.carrier_counter_ref)
            self.message_post(body=msg)
            self.send_email_to_customer()
    
    def send_email_to_customer(self):
        _logger.info("-> send_email_to_customer")
        if self.partner_id.email:
            param = self.env['ir.config_parameter'].sudo()
            mail = {}
            email_subject = "Seguimiento a tu pedido con 99 minutos"
            url = param.sudo().get_param('itl_99_minutos.url_tracking_99minutos')
            email_from = param.sudo().get_param('itl_99_minutos.email_from_tracking_99minutos')
            user_mail = param.sudo().get_param('itl_99_minutos.user_send_email_99minutos')
            user = self.env['res.users'].browse(int(user_mail))
            mail_contain = """Hola {0}, para darle seguimiento a tu pedido puedes acceder al link <a target="_blank" href='{1}' class="btn_pago">Rastrea tu orden</a> y usar tu número de orden <b>{2}</b>.""".format(self.partner_id.name, url, self.carrier_counter_ref)
            mail_obj = False
            if not user_mail:
                mail_obj = self.env['mail.mail'].sudo()
            else:
                mail_obj = self.env['mail.mail'].sudo(user_mail)

            mail_create = mail_obj.create({
                'subject': email_subject,
                'email_from': email_from,
                'recipient_ids': [(6, 0, [self.partner_id.id])],
                'body_html': mail_contain,
                'auto_delete': False
            })
            if mail_create:
                mail_create.send()
                self.message_post(body="Se envió el correo de seguimiento al cliente.")

class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()
        if self._context.get('force_valuation_amount'):
            valuation_amount = self._context.get('force_valuation_amount')
        else:
            valuation_amount = cost

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(valuation_amount)
        # check that all data is correct
        if self.company_id.currency_id.is_zero(debit_value) and not self.env['ir.config_parameter'].sudo().get_param('stock_account.allow_zero_cost'):
            raise UserError(_("The cost of %s is currently equal to 0. Change the cost or the configuration of your product to avoid an incorrect valuation.") % (self.product_id.display_name,))
        credit_value = debit_value


        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        res = [(0, 0, line_vals) for line_vals in self._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id).values()]

        return res