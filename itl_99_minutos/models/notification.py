# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json

import logging
_logger = logging.getLogger(__name__)

class itl_99_minutos_notification(models.Model):
    _name = "itl.99.minutos.notification"
    _inherit = ['mail.thread']

    def _get_default_company(self):
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        company_id = False
        if sr_company_id:
            company_id = self.env['res.company'].browse(int(sr_company_id))

        return company_id
    
    response = fields.Text(string="Response")
    status = fields.Selection([('new','New'),('done','Successfully processed'),('error','Processed without success')], default='new')
    company_id = fields.Many2one('res.company', string="Compañía", readonly=True, store=True, default=_get_default_company)
    
    
    def save_barcode(self):
        _logger.info("--> save_barcode method")
        self._cr.commit()
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id') or False
        if self.response:
            self._cr.autocommit(False)
            try:
                #response = self.fixjson(self.response)
                _logger.info("--> response: " + str(self.response))
                response = str(self.response).replace("\'", "\"")
                json_response = json.loads(response)
                
                tracking_id = json_response['tracking_id']
                _logger.info("-> tracking_id: +" + str(tracking_id) + "+")
                
                stock_picking_id = self.env['stock.picking'].search([('carrier_tracking_ref','=',tracking_id)])
                _logger.info("-> stock_picking_id: " + str(stock_picking_id))
                if stock_picking_id:
                    barcode = json_response['barcode']
                    _logger.info("-> barcode: " + str(barcode))
                    if len(barcode) > 0:
                        _logger.info("--> Tiene barcode")
                        #stock_picking_id.do_unreserve()
                        barcode = barcode.replace(',','')
                        if barcode[-1] == 'F':
                            _logger.info("--> Removiendo F")
                            barcode = barcode[:-1]
                        serie_id = self.env['stock.production.lot'].search([('name','=',barcode)])
                        _logger.info("--> serie_id: " + str(serie_id))
                        if serie_id:
                            _logger.info("--> Se encontró la serie")
                            force_valuation_amount = False
                            if len(serie_id) == 1:
                                serie_id = serie_id[0]
                            else:
                                serie_id = serie_id[1]
                            for stock_line in stock_picking_id.move_ids_without_package:
                                if len(stock_line.move_line_ids) > 0:
                                    stock_line.move_line_ids[0].lot_id = serie_id
                                    stock_line.move_line_ids[0].qty_done = 1
                                    force_valuation_amount = stock_line.move_line_ids[0].product_id.standard_price
                                    _logger.info("-> Changing serie: " + str(stock_line.move_line_ids[0].lot_id))
                                    _logger.info("-> Changing qty: " + str(stock_line.move_line_ids[0].qty_done))
                                    _logger.info("-> Product cost: " + str(stock_line.move_line_ids[0].product_id.standard_price))
                                else:
                                    _logger.info("-> Adding new line")
                                    move_line_add = [(0, 0, {'product_uom_id': stock_line.product_uom.id,
                                                        'picking_id': stock_line.picking_id.id,
                                                        'move_id': stock_line.id,
                                                        'product_id': stock_line.product_id.id,
                                                        'location_id': stock_line.location_id.id,
                                                        'lot_id': serie_id.id,
                                                        'location_dest_id': stock_line.location_dest_id.id,
                                                        'qty_done': 1})]
                                    _logger.info("-> Serie: " + str(serie_id))
                                    _logger.info("-> Qty: " + str(1))
                                    stock_line.move_line_ids = move_line_add
                                    
                            #if not flag_error:
                            _logger.info("-> No errors")
                            #stock_picking_id.action_assign()
                            stock_picking_id.with_context(force_company=sr_company_id,force_valuation_amount=force_valuation_amount).sudo(self.env.user.id).button_validate()
                            _logger.info("--> After stock_picking button_validate")
                            sale_order_id = stock_picking_id.sale_id
                            partner_id = sale_order_id.partner_id
                            partner_id.barcode_99minutos = barcode

                            subscriptions = stock_picking_id.sale_id.order_line.mapped('subscription_id')
                            if subscriptions:
                                subscription_id = subscriptions[0]
                                subscription_id.iccid_number = serie_id.name
                                _logger.info("--> After stock_picking button_validate")
                            #_logger.info("-> Success")
                            sale_id = stock_picking_id.sale_id
                            if sale_id:
                                activemq_message = self.env['activemq.message'].search([('sale_order_id','=',sale_id.id)])
                                if activemq_message:
                                    activemq_message.message_post(body="El mensaje de respuesta se generó con información del ICCID enviada por 99 Minutos.", subject="Registro procesado")
                                    activemq_message.create_response_message()
                                    activemq_message.send_response_message_to_sr()
                                    _logger.info("--> Success send_response_message_to_sr")
                            _logger.info("-> Success")
                            self.status = 'done'
                            self.message_post(body="El registro se procesó correctamente.")
                        else:
                            self.status = 'error'
                            self.message_post(body="No se encontró el número de serie " + str(barcode) + " en el inventario.")
                    else:
                        self.status = 'error'
                        self.message_post(body="No se encontró el barcode en la notificación de 99 minutos.")
                else:
                    self.status = 'error'
                    self.message_post(body="No se encontró el movimiento de salida relacionado al tracking_id: " + str(tracking_id))
                self._cr.commit()
            except Exception as e:
                self._cr.rollback()
                _logger.info("--> Exception: " + str(e))
                self.status = 'error'
                self.message_post(body="Error: " + str(e))
                self.message_post(body="El registro no pudo ser procesado")
                self._cr.commit()
        #raise ValidationError("Testing...")

                        