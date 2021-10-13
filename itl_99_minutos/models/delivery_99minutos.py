
from odoo import models, fields, _
import json
import requests
from odoo.exceptions import UserError, ValidationError
import ast

import logging
_logger = logging.getLogger(__name__)

class NoventayNueveMinutosProvider(models.Model):
    _inherit = "delivery.carrier"


    delivery_type = fields.Selection(selection_add=[('_99minutos', "99minutos")], ondelete={"_99minutos": "cascade"})

    _99m_apikey_prod = fields.Char(string="Apikey prod")
    _99m_apikey_dev = fields.Char(string="Apikey dev")
    _99m_url_prod = fields.Char(string="URL Crear orden prod")
    _99m_url_dev = fields.Char(string="URL Crear orden dev")
    _99m_url_shipping_rate_prod = fields.Char(string="URL Shipping rate prod")
    _99m_url_shipping_rate_dev = fields.Char(string="URL Shipping rate dev")

    _99m_deliveryType = fields.Selection([('sameDay','Envío especial, se entrega el mismo día'),
                                                ('nextDay','Envío estandar, se entrega al siguiente día'),
                                                ('99minutos','Envío express, se entrega en "99 minutos"'),
                                                ('C02','Envío ecológico (exclusivo en nextday)')],
                                                string="Metodo de envío")
    _99m_packageSize = fields.Selection([('xs','XS (1 kg)'),
                                                ('s','S (1 - 2 Kg)'),
                                                ('m','M (2 - 3 Kg)'),
                                                ('l','L (3 - 5 Kg)'),
                                                ('xl','XL (5 - 25 Kg)')],
                                                string="Tamaño del paquete")
    _99m_default_packaging_id = fields.Many2one('product.packaging', string='99minutos Default Packaging Type')


    def _99minutos_rate_shipment(self, order):
        _logger.info("-> _99minutos_rate_shipment")
        self.ensure_one()
        
        ICPSudo = self.env['ir.config_parameter'].sudo()
        delivery_address = ICPSudo.get_param('itl_99_minutos.delivery_address_99_minutos')
        email_from_99minutos = ICPSudo.get_param('itl_99_minutos.email_from_99minutos')
        email_to_99minutos = ICPSudo.get_param('itl_99_minutos.email_to_99minutos')
        res_partner_ids_notification_99minutos = ast.literal_eval(ICPSudo.get_param('itl_99_minutos.res_partner_ids_notification_99minutos'))
        #_logger.info("-----> res_partner_ids_notification_99minutos: " + str(type(res_partner_ids_notification_99minutos)))
        #res_partner_ids_notification_99minutos = [486, 413, 414]
        
        codePostal = False
        if delivery_address:
            delivery_address = self.env['res.partner'].browse(int(delivery_address))
            codePostal = delivery_address.zip
        else:
            codePostal = order.company_id.zip

        if not codePostal:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: the company zip code or delivery address zip code is missing.'),
                    'warning_message': False}
        if not order.partner_shipping_id.zip:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: the customer zip code in delivery address is missing.'),
                    'warning_message': False}
        if not self._99m_default_packaging_id:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: the delivery method has not set Default Packing Type.'),
                    'warning_message': False}
        
        weight = self._99m_default_packaging_id.max_weight
        width = self._99m_default_packaging_id.width
        depth = self._99m_default_packaging_id.packaging_length
        height = self._99m_default_packaging_id.height
        
        if weight == 0:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: the delivery method has not set default weight in Default Packing Type.'),
                    'warning_message': False}
        if width == 0:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: the delivery method has not set default width in Default Packing Type.'),
                    'warning_message': False}
        if depth == 0:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: the delivery method has not set default depth in Default Packing Type.'),
                    'warning_message': False}
        if height == 0:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: the delivery method has not set default height in Default Packing Type.'),
                    'warning_message': False}

        body = {
            "weight": weight,
            "width": width,
            "depth": depth,
            "height": height,
            "origin": {
                "codePostal": codePostal,
                "country": "MEX"
            },
            "destination": {
                "codePostal": order.partner_shipping_id.zip,
                "country": "MEX"
            }
        }
        
        #_logger.info("body: " + str(body))

        auth_token = ""
        url = ""
        if self.prod_environment:
            auth_token = self._99m_apikey_prod
            url = self._99m_url_shipping_rate_prod
        else:
            auth_token = self._99m_apikey_dev
            url = self._99m_url_shipping_rate_dev
            
        body_json = json.dumps(body)
        newHeaders = {'Content-type': 'application/json',
                    'Authorization': 'Bearer ' + auth_token
        }
        
        response_json = False
        try:
            response = requests.post(url, data=body_json, headers=newHeaders)
            #_logger.info("response: " + str(response.json()))
            response_json = response.json()
            #_logger.info("response_json: " + str(response_json))
        except Exception as e:
            return {'success': False,
                    'price': 0.0,
                    'error_message': str("Error en la petición: " + str(e)),
                    'warning_message': False}
        
        price = 0.0
        flag = False
        #_logger.info("-> response status: " + str(response.status_code))
        if response.status_code == 200:
            for n in  response_json['message']:
                delivery_method = str(n['deliveryType']['description']).lower()
                dm = str(self._99m_deliveryType).lower()
                if dm in delivery_method:
                    price = n['cost']
                    flag = True
                    break
        if response.status_code == 400 or response.status_code == 404:
            #_logger.info("response_: " + str(response_json))
            message = response_json['message']
            error_message = message
            
            if error_message == 'Wrong APIKEY':
                return {'success': False,
                    'price': 0.0,
                    'error_message': error_message,
                    'warning_message': False}

            if 'title' in error_message:
                error_message = error_message['title']

                if error_message == 'Sin cobertura':

                    if not res_partner_ids_notification_99minutos:
                        order.message_post(body="No se pudo enviar el email de notificación de no cobertura porque no están configurados los contactos destinatarios.")
                        return {'success': False,
                            'price': 0.0,
                            'error_message': error_message,
                            'warning_message': False}
                    mail_vals = {}
                    if email_from_99minutos:
                        mail_vals.update({'email_from': email_from_99minutos})

                    mail_contain = "<p>La Sale Order " + str(order.name) + " no tiene cobertura de envío con 99 minutos</p>"
                    mail_vals.update({
                                    'subject': "Pedido sin cobertura",
                                    'recipient_ids': [(6, 0, res_partner_ids_notification_99minutos)],
                                    'body_html': mail_contain,
                                    'auto_delete': False
                                })
                    mail_create = self.env['mail.mail'].create(mail_vals)
                    if mail_create:
                        mail_create.send()
                        emails_name = ''
                        res_partner_ids = self.env['res.partner'].browse(res_partner_ids_notification_99minutos)
                        
                        for rp in res_partner_ids:
                            emails_name += rp.email + ', '
                        order.message_post(body="La Sale Order " + str(order.name) + " no tiene cobertura de envío con 99 minutos. Notificación enviada por correo electrónico a las direcciones: " + str(emails_name))
                    
                    
                    return {'success': False,
                            'price': 0.0,
                            'error_message': error_message,
                            'warning_message': False}
                else:
                    return {'success': False,
                            'price': 0.0,
                            'error_message': error_message,
                            'warning_message': False}
        
        results = str(response_json)
        if not flag:
            warning_message = """No se encontró un resultado para el Método de envío seleccionado.\n
                                Resultados encontrados:\n
                                """ + results
            return {'success': False,
                    'price': 0.0,
                    'error_message': warning_message,
                    'warning_message': False}

        return {'success': True,
                    'price': price,
                    'error_message': False,
                    'warning_message': False}

    def _99minutos_send_shipping(self, pickings):
        _logger.info("-> _99minutos_send_shipping")
        res = []

        for picking in pickings:
            apikey = ""
            if picking.carrier_id.prod_environment:
                apikey = picking.carrier_id._99m_apikey_prod
            else:
                apikey = picking.carrier_id._99m_apikey_dev

            addresOrigin = ""

            if picking.company_id.street_name:
                addresOrigin += picking.company_id.street_name
            if picking.company_id.street_number:
                addresOrigin += ", " + picking.company_id.street_number
            if picking.company_id.street_number2:
                addresOrigin += ", " + picking.company_id.street_number2
            if picking.company_id.zip:
                addresOrigin += ", " + picking.company_id.zip
            if picking.company_id.l10n_mx_edi_colony:
                addresOrigin += ", " + picking.company_id.l10n_mx_edi_colony
            if picking.company_id.state_id:
                addresOrigin += ", " + picking.company_id.state_id.name
            if picking.company_id.country_id:
                addresOrigin += ", " + picking.company_id.country_id.name
                
            ICPSudo = self.env['ir.config_parameter'].sudo()
            delivery_address = ICPSudo.get_param('itl_99_minutos.delivery_address_99_minutos')

            #codePostal = False
            addressOrigin = ''
            numberOrigin = ''
            codePostalOrigin = ''
            if delivery_address:
                delivery_address = self.env['res.partner'].browse(int(delivery_address))
                addressOrigin = self.build_address(delivery_address)
                
                numberOrigin = delivery_address.street_number or delivery_address.street_number2 or ""
                codePostalOrigin = delivery_address.zip or ""
            else:
                addressOrigin = self.build_address(picking.company_id)
                
                numberOrigin = picking.company_id.street_number or picking.company_id.street_number2 or ""
                codePostalOrigin = picking.company_id.zip or ""

            addressDest = self.build_address(picking.partner_id)
            _logger.info("--> addressOrigin: " + str(addressOrigin))
            _logger.info("--> addressDest: " + str(addressDest))
            body = {"apikey": apikey,
                    "deliveryType": picking.carrier_id._99m_deliveryType,
                    "packageSize": picking.carrier_id._99m_packageSize,
                    "notes": "",
                    "cahsOnDelivery": False,
                    "amountCash": 0,
                    "SecurePackage": False,
                    "amountSecure": 0,
                    "receivedId": "",
                    "origin": {
                        "sender": picking.company_id.name,
                        "nameSender": picking.company_id.name,
                        "lastNameSender": "",
                        "emailSender": picking.company_id.email or "",
                        "phoneSender": picking.company_id.phone or "",
                        "addressOrigin": addressOrigin,
                        "numberOrigin": numberOrigin,
                        "codePostalOrigin": codePostalOrigin,
                        "country": "MEX"
                    },
                    "destination":{
                        "receiver": picking.partner_id.name,
                        "nameReceiver": picking.partner_id.name,
                        "lastNameReceiver": "",
                        "emailReceiver": picking.partner_id.email or "",
                        "phoneReceiver": picking.partner_id.phone or picking.partner_id.mobile or "",
                        "addressDestination": addressDest,
                        "numberDestination": ((picking.partner_id.street_number or "") + " " + (picking.partner_id.street_number2 or "")).strip(),
                        "codePostalDestination": picking.partner_id.zip or "",
                        "country": "MEX"
                    }
            }
            #raise ValidationError("Testing...")
            url = ""
            if picking.carrier_id.prod_environment:
                url = picking.carrier_id._99m_url_prod
            else:
                url = picking.carrier_id._99m_url_dev
            
            body_json = json.dumps(body, ensure_ascii=False)
            newHeaders = {'Content-type': 'application/json'}
            response = requests.post(url, data=body_json, headers=newHeaders)
            response_json = response.json()
            itl_response = []
            itl_data_response = {}
            tracking_number = False
            counter_number = False
            itl_99minutos_order = self.env['itl.99.minutos.order']
            if response.status_code == 201:
                tracking_number = response_json['message'][0]['reason']['trackingid']
                counter_number = response_json['message'][0]['reason']['counter']
            else:
                #_logger.info(str("Ocurrió un error al realizar la solicitud: " + str(response.status_code) +"\n" + "message: " + str(response_json['message'][0]['message'])))
                #res = res
                vals = {
                    'operation_type': 'create_order',
                    'status_code': str(response.status_code),
                    'url_body': str(body_json),
                    'response': str(response_json),
                    'url_used': str(url),
                    'stock_picking_id': picking.id
                }
                itl_99minutos_order.create(vals)
                return False
                #raise ValidationError(str("Ocurrió un error al realizar la solicitud: " + str(response.status_code) +"\n" + "message: " + str(response_json['message'][0]['message'])))
            
            price = 0.0
            #_logger.info("-> picking.sale_id: " + str(picking.sale_id))
            #_logger.info("-> picking.sale_id.delivery_price: " + str(picking.sale_id.delivery_price))
            if picking.sale_id:
                price = picking.sale_id.delivery_price

            shipping_data = {
                'exact_price':  price,
                'tracking_number': tracking_number,
                'counter_number': counter_number
            }
            res = res + [shipping_data]

            vals = {
                    'operation_type': 'create_order',
                    'status_code': str(response.status_code),
                    'url_body': str(body_json),
                    'response': str(response_json),
                    'url_used': str(url),
                    'stock_picking_id': picking.id
                }
            itl_99minutos_order.create(vals)

        return res

    def build_address(self, partner_id):
        calle = (partner_id.street_name or "") + " "
        codigo_p = (partner_id.zip or "") + ", "
        colonia = (partner_id.l10n_mx_edi_colony or "") + ", "
        estado = (partner_id.itl_state or "") + ", "
        ciudad = (partner_id.city or "") + ", "
        pais = (partner_id.country_id.name or "México")

        addressOrigin = calle + colonia + codigo_p + ciudad + estado + pais

        return addressOrigin