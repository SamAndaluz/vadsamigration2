from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import xmltodict
from uuid import uuid4
import json
from datetime import date
from dateutil.parser import parse

import logging
_logger = logging.getLogger(__name__)

class ActivemqMessage(models.Model):
    _name = "activemq.message"
    _inherit = ['mail.thread']

    def _get_default_company(self):
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        company_id = self.env['res.company'].browse(int(sr_company_id))

        return company_id

    name = fields.Char(string="Tipo de mensaje")
    message_id = fields.Char(string="messageID del mensaje", store=True, copy=False)
    service_source = fields.Char(string="Service source", store=True, copy=False)
    already_processed = fields.Boolean(string='Ya procesado en DoPlaceOrderEvent', store=True, copy=False)
    product_category = fields.Selection([('addOn','AddOn'),
                                        ('plan','Plan'),
                                        ('activation','Activation'),
                                        ('balanceTransform','Transform'),
                                        ('balanceTransfer','Transfer (Gift)'),
                                        ('voicemail','Voicemail'),
                                        ('portIn','PortIn'),
                                        ('other','Otro')], string="Categoría de producto", help="Categoría del producto de SR")
    delivery_type = fields.Selection([('99minutos','Envío con 99 Minutos'),('already_have_a_sim','Already have a SIM'),('rokit','ROKiT'),('assignSim','Assign Sim')], string="Tipo de entrega", copy=False)
    xml_message = fields.Text(string="Mensaje XML")
    status = fields.Selection([('new','Nuevo'),('done','Procesado correctamente'),('error','Error al procesar')], default='new', copy=False)

    invoice_id = fields.Many2one('account.invoice', string="Factura", store=True, copy=False)
    sale_order_id = fields.Many2one('sale.order', string="Orden de venta", store=True, copy=False)
    sale_delivery_message = fields.Char(related="sale_order_id.delivery_message", string="Mensaje de entrega")
    sale_subscription_id = fields.Many2one('sale.subscription', string="Suscripción", store=True, copy=False)
    customer_id = fields.Many2one('res.partner', related="sale_subscription_id.partner_id", string="Cliente", store=True, copy=False)
    iccid_number = fields.Char(related="sale_subscription_id.iccid_number", string="ICCID", readonly=True)
    msisdn_number = fields.Char(related="sale_subscription_id.msisdn_number", string="MSISDN", readonly=True)
    order_ref_id = fields.Char(related="sale_subscription_id.order_ref_id", string="orderRefId del mensaje", readonly=True)
    account_id_ref = fields.Char(related="sale_subscription_id.account_id_ref", string="CMP account", readonly=True)
    subscription_id_ref = fields.Char(related="sale_subscription_id.subscription_id_ref", string="Suscripción CMP", readonly=True)
    subscription_id = fields.Many2one('sale.subscription.template', string="Plantilla de la suscripción", store=True, copy=False)
    company_id = fields.Many2one('res.company', string="Compañía", store=True, default=_get_default_company)
    log_id = fields.Many2one("sr.get.message.log", string="Log Message", store=True, copy=False)
    response_message = fields.Text(string="Respuesta para Separate Reality", store=True, copy=False)
    response_message_status = fields.Selection([('new','Nuevo'),('done','Enviado correctamente'),('error','Error al enviar')], copy=False)
    reason = fields.Char(string="Razón", store=True, copy=False)
    activation_subscription_id = fields.Char(string="Suscripción", copy=False)
    activation_line_identifier = fields.Char(string="MSISDN", copy=False)

    has_permission_admin = fields.Boolean(compute="_check_permissions")

    def _check_permissions(self):
        self.has_permission_admin = False
        if self.env.user.has_group('itl_sr_interface.group_sr_admin'):
            self.has_permission_admin = True
            

    def send_response_to_queue(self):
        error = False
        message_error = ''
        if not self.sale_subscription_id.order_ref_id:
            error = True
            message_error += "No se encontró 'orderRefId' en el campo Message response. "
            #raise UserError("No se encontró 'orderRefId' en el campo Message response.")
        if not self.sale_subscription_id.iccid_number:
            error = True
            message_error += "No se encontró 'iccid' en el campo Message response. "
            #raise UserError("No se encontró 'iccid' en el campo Message response.")
        if not self.sale_subscription_id.msisdn_number:
            error = True
            message_error += "No se encontró 'msisdn' en el campo Message response. "
            #raise UserError("No se encontró 'msisdn' en el campo Message response.")
        if not self.reason:
            error = True
            message_error += "No se encontró 'reason' en el campo Message response. "
            #raise UserError("No se encontró 'reason' en el campo Message response.")
        
        if error:
            self.response_message_status = 'error'
            self.message_post(body="El mensaje de respuesta no pudo ser enviado a Separate Reality. " + message_error, subject="Registro procesado")
            return

        if not self.response_message:
            self.create_response_message()

        self.send_response_message_to_sr()

    def create_sale_order_addon(self, sale_subscription_id, product_id, total_amount):
        product_id = product_id.with_context(lang='es_MX')
        name = self.env['sale.order.line'].get_sale_order_line_multiline_description_sale(product_id)
        option_line_vals = {'name': name, 'product_id': product_id.id, 'uom_id': product_id.uom_id.id}
        subs_wizard_vals = {'subscription_id': sale_subscription_id.id}
        subs_wizard = self.env['sale.subscription.wizard'].create(subs_wizard_vals)
        subs_wizard.option_lines = [(0, 0, option_line_vals)]

        total_amount = float(total_amount) / 100
        total_untaxed_amount = float(total_amount) / 1.16

        sale_order_id = subs_wizard.with_context({'price_unit': total_untaxed_amount, 'discount': 0}).itl_create_sale_order()

        return sale_order_id

    def do_place_service_order_event_multi(self):
        invalid_records = self.filtered(lambda r: r.name != 'DoPlaceServiceOrderEvent')
        if len(invalid_records) > 0:
            raise ValidationError("Algunos registros no son de tipo DoPlaceServiceOrderEvent.")

        self.do_place_service_order_event()


    def do_place_service_order_event(self):
        for record in self:
            try:
                param = self.env['ir.config_parameter'].sudo()
                sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
                if not record.company_id:
                    record.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
                exception_message = []
                record.reload_xml_message()
                if record.status in ['new','error']:
                    if record.service_source == 'VADSA-CMP':
                        if not record.already_processed:
                            xml_doc = xmltodict.parse(record.xml_message)

                            normal_order = False
                            product_info = False
                            service_legacy_id = False
                            sale_subscription_id = False
                            is_rokit = False

                            _logger.info("-> Proccessing")
                            DoPlaceServiceOrderEvent = xml_doc['DoPlaceServiceOrderEvent']
                            if not 'addItems' in DoPlaceServiceOrderEvent or DoPlaceServiceOrderEvent['addItems'] == None:
                                exception_message.append("El mensaje no contiene información para el addOn en la etiqueta addItems.")
                                raise ValidationError("Error en validaciones.")
                            item = xml_doc['DoPlaceServiceOrderEvent']['addItems']['item']
                            # Activation Order
                            if 'modifyServiceDetails' in item:
                                modifyServiceDetails = item['modifyServiceDetails']
                                if 'productLegacyId' in modifyServiceDetails and record.company_id.sr_activation_legacy_product_name in modifyServiceDetails['productLegacyId']:
                                    normal_order = True
                                    record.product_category = 'activation'
                            # Balance Transform Order
                            if 'balanceTransform' in item:
                                balanceTransform = item['balanceTransform']
                                if 'subCategory' in balanceTransform and 'BalanceTransform' in balanceTransform['subCategory']:
                                    normal_order = True
                                    record.product_category = 'balanceTransform'
                            # Balance Transfer Order
                            if 'balanceTransfer' in item:
                                balanceTransfer = item['balanceTransfer']
                                if 'subCategory' in balanceTransfer and 'BalanceTransfer' in balanceTransfer['subCategory']:
                                    normal_order = True
                                    record.product_category = 'balanceTransfer'
                            # Voicemail Order
                            if 'booleanValueAddedService' in item:
                                booleanValueAddedService = item['booleanValueAddedService']
                                if 'productLegacyId' in booleanValueAddedService and 'VMS' in booleanValueAddedService['productLegacyId']:
                                    normal_order = True
                                    record.product_category = 'voicemail'
                            # Portin Order
                            if 'portIn' in item:
                                portIn = item['portIn']
                                if 'productLegacyId' in portIn and 'VADSA-PORT-IN' in portIn['productLegacyId']:
                                    normal_order = True
                                    record.product_category = 'portIn'
                            if not normal_order and not 'addOn' in item:
                                exception_message.append("El mensaje no contiene información del addOn.")
                                raise ValidationError("Error en validaciones.")
                            if 'account' in item and 'accountLegacyId' in item['account']:
                                account_legacy_id = item['account']['accountLegacyId']
                            if 'service' in item and 'serviceLegacyId' in item['service']:
                                service_legacy_id = item['service']['serviceLegacyId']
                                line_identifier = item['service']['lineIdentifier']
                            if 'addOn' in item:
                                product_info = item['addOn']

                            if normal_order:
                                record.activation_subscription_id = service_legacy_id
                                record.activation_line_identifier = line_identifier
                                record.status = 'done'
                                record.message_post(body="El registro se procesó correctamente.", subject="Registro procesado")

                                continue
                            
                            creation_date = item['creationDate']
                            creation_date = parse(str(creation_date))

                            total_amount = item['total']
                            _logger.info("-> service_legacy_id: " + str(service_legacy_id))
                            if service_legacy_id:
                                sale_subscription_id = self.env['sale.subscription'].search([('subscription_id_ref','=',service_legacy_id),('company_id','=',record.company_id.id)], limit=1)
                                _logger.info("-> sale_subscription_id: " + str(sale_subscription_id))
                                if sale_subscription_id:
                                    subscription_template_id = sale_subscription_id.template_id
                                    record.sale_subscription_id = sale_subscription_id
                                    #self.customer_id = sale_subscription_id.partner_id
                            if not service_legacy_id or not sale_subscription_id:
                                exception_message.append("No se encontró la suscripción relacionada al número " + str(service_legacy_id) + ".")
                                raise ValidationError("Error en validaciones.")
                            _logger.info("-> After get subscription info")
                            # Product plan
                            product_id = False
                            product_category = 'addOn'
                            _logger.info("-> subscription_template_id: " + str(subscription_template_id))
                            if product_info and subscription_template_id:
                                product_id = self.env['product.product'].search([('productLegacyId','=',product_info['productLegacyId']),('subscription_template_id','=',subscription_template_id.id)])
                                _logger.info("-> product_id: " + str(product_id))
                                if not product_id:
                                    product_id = record.with_context(force_company=record.company_id.id).create_product_subscription(product_info, subscription_template_id, product_category, is_rokit)
                            else:
                                exception_message.append("No se pudo obtener el producto de la suscripción.")
                                raise ValidationError("Error en validaciones.")
                            #product_id.productCategory = product_category
                            record.product_category = product_category
                            _logger.info("-> After get product info")
                            # Create SO and confirm it
                            if not record.sale_order_id:
                                sale_order_id = record.with_context(force_company=record.company_id.id).create_sale_order_addon(sale_subscription_id, product_id, total_amount)
                                record.sale_order_id = sale_order_id
                                sale_order_id.action_confirm()
                            else:
                                sale_order_id = record.sale_order_id
                                if sale_order_id.state in ['draft','sent']:
                                    sale_order_id.action_confirm()
                            
                            _logger.info("-> After create sale order")
                            
                            # Create invoice and confirm it
                            if not record.invoice_id:
                                invoice_id = record.with_context(force_company=record.company_id.id).create_invoice(sale_order_id)
                                record.invoice_id = invoice_id
                                invoice_id.action_invoice_open()
                            else:
                                invoice_id = record.invoice_id
                                if invoice_id.state in ['draft']:
                                    invoice_id.action_invoice_open()
                            
                            _logger.info("-> After create invoice")
                            _logger.info("--> invoice_id.l10n_mx_edi_cfdi_uuid: " + str(invoice_id.l10n_mx_edi_cfdi_uuid))
                            if invoice_id.l10n_mx_edi_cfdi_uuid:
                                if not invoice_id.state == 'paid':
                                    # Create payment
                                    payment = record.with_context(force_company=record.company_id.id).create_payment(invoice_id)
                                    payment.post()
                                    _logger.info("-> After pay invoice")

                                    record.send_mail(invoice_id)

                                record.status = 'done'

                                record.message_post(body="El registro se procesó correctamente.", subject="Registro procesado")    
                            else:
                                record.status = 'error'
                                record.message_post(body="El registro no se procesó correctamente. La factura creada parece no estar firmada.", subject="Registro no procesado")
                        else:
                            exception_message.append("Este plan ya fue procesado en el registro DoPlaceOrderEvent con orderRefId: " + str(record.message_id))
                            raise ValidationError("Error en validaciones.")
                    else:
                        exception_message.append("Este registro no contiene información del plan.")
                        raise ValidationError("Error en validaciones.")

                if record.status == 'done':
                    if record.invoice_id and record.invoice_id.state == 'open' and record.invoice_id.l10n_mx_edi_cfdi_uuid:
                        payment = record.create_payment(record.invoice_id)
                        payment.post()
            except Exception as e:
                record.message_post(body="Exception: " + str(e.args[0]), subject="Registro no procesado")
                record.status = 'error'
                if len(exception_message) > 0:
                    error_messages = ""
                    for e in exception_message:
                        error_messages += e + '\n'
                    record.message_post(body="Advertencia: \n" + error_messages, subject="Registro no procesado")

    def do_place_order_event(self):
        _logger.info("--> do_place_order_event")
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        if not self.company_id:
            self.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        sr_rokit_product_id = self.company_id.sr_rokit_product_id
        for record in self:
            exception_message = []
            try:
                _logger.info("--> do_place_order_event try")
                record.reload_xml_message()
                _logger.info("--> after record.reload_xml_message")
                if record.status in ['new','error']:
                    _logger.info("-> Proccessing")
                    xml_doc = xmltodict.parse(record.xml_message)
                    _logger.info("---> after xmltodict.parse")
                    error_flag = False

                    plan_info = False
                    product_info = False
                    iccid = False
                    reason = 'NewCustomer'
                    msisdn = False
                    account_legacy_id = False
                    service_legacy_id = False
                    serviceItems = xml_doc['DoPlaceOrderEvent']['order']['serviceAddItems']['item']
                    is_assignSim = False
                    is_rokit = False
                    has_product = False
                    #_logger.info("-> serviceItems: " + str(serviceItems))
                    for index, service_item in enumerate(serviceItems):
                        if 'account' in service_item and 'accountLegacyId' in service_item['account']:
                            account_legacy_id = service_item['account']['accountLegacyId']
                        if 'service' in service_item and 'serviceLegacyId' in service_item['service']:
                            service_legacy_id = service_item['service']['serviceLegacyId']
                        if 'plan' in service_item:
                            plan_info = service_item['plan']
                            #_logger.info("--> service_item['extendedData']: " + str(json.loads(service_item['extendedData'])['ICCID']))
                            if 'extendedData' in service_item and service_item['extendedData'] != None:
                                _logger.info("--> plan extendedData" )
                                _logger.info("--> plan extendedData: " + str(service_item['extendedData']) )
                                extendedData = json.loads(service_item['extendedData'])
                                _logger.info("--> after plan extendedData" )
                                if 'reservedMsisdn' in extendedData:
                                    msisdn = extendedData['reservedMsisdn']
                                if 'reason' in extendedData:
                                    reason = extendedData['reason']
                                if 'ICCID' in extendedData:
                                    iccid = extendedData['ICCID']
                            if 'extendedDataXml' in service_item and service_item['extendedDataXml'] != None:
                                _logger.info("--> plan extendedDataXml" )
                                extendedDataXml = service_item['extendedDataXml']
                                if not msisdn and 'reservedMsisdn' in extendedDataXml:
                                    msisdn = extendedDataXml['reservedMsisdn']
                        if 'addOn' in service_item:
                            product_info = service_item['addOn']
                            has_product = True
                            _logger.info("---> ENTRO tiene addOn")
                            if product_info['productName'] in ['ROKiT',sr_rokit_product_id.name] or product_info['productLegacyId'] in ['011076',sr_rokit_product_id.productLegacyId]:
                                is_rokit = True
                            if 'extendedData' in service_item and service_item['extendedData'] != None:
                                _logger.info("--> addOn extendedData" )
                                extendedData = json.loads(service_item['extendedData'])
                                if not msisdn and 'reservedMsisdn' in extendedData:
                                    msisdn = extendedData['reservedMsisdn']
                                if not reason and 'reason' in extendedData:
                                    reason = extendedData['reason']
                                if not iccid and 'ICCID' in extendedData:
                                    iccid = extendedData['ICCID']
                            if 'extendedDataXml' in service_item and service_item['extendedDataXml'] != None:
                                _logger.info("--> addOn extendedDataXml" )
                                extendedDataXml = service_item['extendedDataXml']
                                if not msisdn and 'reservedMsisdn' in extendedDataXml:
                                    msisdn = extendedDataXml['reservedMsisdn']
                        if 'assignSim' in service_item:
                            assignsim_product_info = service_item['assignSim']
                            if assignsim_product_info['productName'] == 'assignSim':
                                is_assignSim = True
                            if 'extendedData' in service_item and service_item['extendedData'] != None:
                                _logger.info("--> assignSim extendedData" )
                                extendedData = json.loads(service_item['extendedData'])
                                if not msisdn and 'reservedMsisdn' in extendedData:
                                    msisdn = extendedData['reservedMsisdn']
                                if not reason and 'reason' in extendedData:
                                    reason = extendedData['reason']
                                if not iccid and 'ICCID' in extendedData:
                                    iccid = extendedData['ICCID']
                            if 'extendedDataXml' in service_item and service_item['extendedDataXml'] != None:
                                _logger.info("--> assignSim extendedDataXml" )
                                extendedDataXml = service_item['extendedDataXml']
                                if not msisdn and 'reservedMsisdn' in extendedDataXml:
                                    msisdn = extendedDataXml['reservedMsisdn']
                        if 'dispatchSim' in service_item:
                            _logger.info("--> dispatchSim" )
                            if not msisdn and 'extendedDataXml' in service_item and service_item['extendedDataXml'] != None and 'reservedMsisdn' in service_item['extendedDataXml']:
                                msisdn = service_item['extendedDataXml']['reservedMsisdn']
                            if not reason and 'extendedDataXml' in service_item and service_item['extendedDataXml'] != None and 'reason' in service_item['extendedDataXml']:
                                reason = service_item['extendedDataXml']['reason']
                            if not iccid and 'extendedDataXml' in service_item and service_item['extendedDataXml'] != None and 'ICCID' in service_item['extendedDataXml']:
                                iccid = service_item['extendedDataXml']['ICCID']
                    
                    if has_product or is_rokit:
                        is_assignSim = False

                    record.reason = reason
                    _logger.info("-> reservedMsisdn: " + str(msisdn))
                    _logger.info("-> reason: " + str(reason))
                    _logger.info("-> ICCID: " + str(iccid))
                    # Customer info           
                    customer_id_ref = xml_doc['DoPlaceOrderEvent']['order']['customerId']
                    creation_date = xml_doc['DoPlaceOrderEvent']['order']['creationDate']
                    order_ref_id = xml_doc['DoPlaceOrderEvent']['order']['orderRefId']
                    creation_date = parse(str(creation_date))

                    token_info = False

                    total_amount = xml_doc['DoPlaceOrderEvent']['order']['total']
                    if 'paymentAuthorization' in xml_doc['DoPlaceOrderEvent']['order']:
                        token_info = xml_doc['DoPlaceOrderEvent']['order']['paymentAuthorization']
                    _logger.info("--> total_amount: " + str(total_amount))
                    #_logger.info("--> product_info: " + str(product_info))
                    #if product_info:
                    #    if 'extendedDataXml' in product_info:
                    #        card_info = product_info['extendedDataXml']
                    
                    customer_id = self.env['res.partner'].search([('customer_id_ref','=',customer_id_ref),('active','=',True)])
                    _logger.info("--> customer_id: " + str(customer_id))
                    if not customer_id:
                        customer_id, message = record.create_customer(xml_doc, token_info, customer_id_ref)
                        if message:
                            exception_message.append(message)
                    #else:
                    #    _logger.info("--> Adding delivery address")
                    #    customer_info = xml_doc['DoPlaceOrderEvent']['order']['accountAddItems']['item']['extendedData']
                    #    customer_info = json.loads(customer_info)
                    #    customer_info_detail = customer_info['personalDetails']
                    #    customer_address_info = customer_info['deliveryAddress']
                    #    customer_id = record.create_customer_delivery_address(customer_address_info, customer_info_detail, customer_id)
                    #self.customer_id = customer_id
                    _logger.info("-> After create_customer")
                    # end Customer info

                    # Plan info (subscription)      
                    #plan_info = xml_doc['DoPlaceOrderEvent']['order']['serviceAddItems']['item'][1]['plan']
                    subscription_template_id = False
                    if plan_info:
                        #_logger.info("-> plan_info: " + str(plan_info))
                        subscription_template_id = self.env['sale.subscription.template'].search([('code','=',plan_info['productLegacyId'])])
                        if not subscription_template_id:
                            subscription_template_id = record.create_subscription_template(plan_info)
                        record.subscription_id = subscription_template_id
                    else:
                        exception_message.append("No se creó el template de la suscripción")
                        error_flag = True
                    _logger.info("-> After create subscription_template")
                    # end Plan info
                    product_category = 'plan'
                    if is_assignSim:
                        subscription_id = record.create_subscription(customer_id, subscription_template_id, sr_company_id)
                        record.sale_subscription_id = subscription_id
                        subscription_id.iccid_number = iccid
                        subscription_id.msisdn_number = msisdn
                        subscription_id.account_id_ref = account_legacy_id
                        subscription_id.subscription_id_ref = service_legacy_id
                        subscription_id.order_ref_id = order_ref_id
                        subscription_id.partner_id_ref = customer_id_ref

                        record.product_category = product_category
                        record.delivery_type = 'assignSim'
                        record.status = 'done'
                        record.message_post(body="El registro se procesó correctamente.", subject="Registro procesado")

                        continue

                    # Product plan
                    #product_info = xml_doc['DoPlaceOrderEvent']['order']['serviceAddItems']['item'][0]['addOn']
                    product_id = False
                    
                    if product_info and subscription_template_id:
                        product_id = self.env['product.product'].search([('productLegacyId','=',product_info['productLegacyId']),('subscription_template_id','=',subscription_template_id.id)])
                        _logger.info("-> product_id: " + str(product_id))
                        if not product_id:
                            product_id = record.create_product_subscription(product_info, subscription_template_id, product_category, is_rokit)
                        #else:
                        #    param = self.env['ir.config_parameter'].sudo()
                        #    sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
                        #    if not self.company_id:
                        #        self.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
                        #    sr_tax_id = self.company_id.sr_tax_id
                        #    price_product = product_id.list_price
                        #    price = float(product_info['upfrontCost']) / 100
                        #    untaxed_price = price / 1.16
                        #    if price_product != untaxed_price:
                        #        product_id.list_price = untaxed_price - 1
                        #    if not product_id.taxes_id or sr_tax_id.id not in product_id.taxes_id.mapped('id'):
                        #        _logger.info("-> changing taxes")
                        #        product_id.taxes_id = [(6, 0, [sr_tax_id.id])]

                    else:
                        exception_message.append("No se pudo obtener el producto de la suscripción")
                        error_flag = True
                    _logger.info("-> is_rokit: " + str(is_rokit))
                    #product_id.productCategory = product_category
                    record.product_category = product_category
                    _logger.info("-> After create product subscription")

                    #stock_quant = False
                    if iccid:
                        iccid = str(iccid)
                        if iccid[-1] == 'F':
                            iccid = iccid[:-1]

                    #    stock_quant = self.search_serial(iccid)

                    #    if not stock_quant:
                    #        exception_message.append("No se encontró el Número de serie/ICCID en el sistema.")
                    #        error_flag = True
                    
                    if error_flag:
                        error_messages = ""
                        for e in exception_message:
                            error_messages += e + '\n' + ', '
                        record.message_post(body="Advertencia: " + error_messages, subject="Registro no procesado")
                        #self.status = 'error'
                        #return True
                    # end Product plan
                    
                    #warehouse_id = False
                    #change_serial = False
                    #if stock_quant:
                    #    change_serial = True
                    #    warehouse = self.env['stock.warehouse'].search([('lot_stock_id','=',stock_quant.location_id.id)])
                    #    if warehouse and len(warehouse) > 0:
                    #        warehouse_id = warehouse[0]

                    # Create SO and confirm it
                    if not record.sale_order_id:
                        sale_order_id = record.create_sale_order(customer_id, product_id, iccid, total_amount)
                        record.sale_order_id = sale_order_id
                        sale_order_id.action_confirm()
                    else:
                        sale_order_id = record.sale_order_id
                        if sale_order_id.state in ['draft','sent']:
                            sale_order_id.action_confirm()
                    #_logger.info("--> sale_order_id.has_delivery: " + str(sale_order_id.has_delivery))
                    #if sale_order_id.has_delivery:
                    #    self.message_post(body="La Sale Order creado tiene cobertura de 99 minutos, el ICCID se obtendrá de la respuesta de 99 minutos.", subject="Registro procesado")
                    #else:
                    #    self.message_post(body="La Sale Order creada no tiene cobertura de 99 minutos, el ICCID deberá ser asignado manualmente desde la Orden de Entrega de la Sale Order.", subject="Registro procesado")
                    _logger.info("-> After create sale order")
                    subscriptions = sale_order_id.order_line.mapped('subscription_id')
                    if subscriptions:
                        subscription_id = subscriptions[0]
                        record.sale_subscription_id = subscription_id
                        record.sale_subscription_id.iccid_number = iccid
                        record.sale_subscription_id.msisdn_number = msisdn
                        record.sale_subscription_id.account_id_ref = account_legacy_id
                        record.sale_subscription_id.subscription_id_ref = service_legacy_id
                        record.sale_subscription_id.order_ref_id = order_ref_id
                        record.sale_subscription_id.partner_id_ref = customer_id_ref

                    # Create invoice and confirm it
                    if not record.invoice_id:
                        invoice_id = record.create_invoice(sale_order_id)
                        _logger.info("--> invoice_id.l10n_mx_edi_cfdi_uuid: " + str(invoice_id.l10n_mx_edi_cfdi_uuid))
                        record.invoice_id = invoice_id
                        if is_rokit:
                            invoice_id.with_context(not_sign=True).action_invoice_open()
                        else:
                            invoice_id.action_invoice_open()
                    else:
                        invoice_id = record.invoice_id
                        if invoice_id.state in ['draft'] and not is_rokit:
                            invoice_id.action_invoice_open()
                        if invoice_id.state in ['draft'] and is_rokit:
                            invoice_id.with_context(not_sign=True).action_invoice_open()
                    _logger.info("-> After create invoice")
                    _logger.info("--> invoice_id.l10n_mx_edi_cfdi_uuid: " + str(invoice_id.l10n_mx_edi_cfdi_uuid))
                    if invoice_id.l10n_mx_edi_cfdi_uuid:
                        if not invoice_id.state == 'paid':
                            # Create payment
                            payment = record.create_payment(invoice_id)
                            payment.post()
                            _logger.info("-> After pay invoice")

                            record.send_mail(invoice_id)

                        record.status = 'done'

                        record.message_post(body="El registro se procesó correctamente.", subject="Registro procesado")
                    elif is_rokit:
                        record.status = 'done'
                        record.message_post(body="El registro se procesó correctamente.", subject="Registro procesado")
                    else:
                        record.status = 'error'
                        record.message_post(body="El registro no se procesó correctamente. La factura creada parece no estar firmada.", subject="Registro no procesado")
                    if iccid:
                        record.delivery_type = 'already_have_a_sim'
                        if is_rokit:
                            record.delivery_type = 'rokit'
                        if (not record.response_message_status or record.response_message_status not in ['new','error']) and not is_rokit:
                            record.create_response_message(iccid)
                            record.send_response_message_to_sr()
                    else:
                        record.delivery_type = '99minutos'

                if record.status == 'done':
                    if record.invoice_id and record.invoice_id.state == 'open' and record.invoice_id.l10n_mx_edi_cfdi_uuid:
                        payment = record.create_payment(record.invoice_id)
                        payment.post()
            except Exception as e:
                record.message_post(body="Exception: " + str(e), subject="Registro no procesado")
                record.status = 'error'
                if len(exception_message) > 0:
                    error_messages = ""
                    for e in exception_message:
                        error_messages += e + '\n'
                    record.message_post(body="Advertencia: \n" + error_messages, subject="Registro no procesado")

    def create_subscription(self, customer_id, subscription_template_id, sr_company_id):
        subscription_obj = self.env['sale.subscription']
        pricelist_id = subscription_obj._get_default_pricelist()
        subscription_vals = {
            'name': "New",
            'pricelist_id': pricelist_id,
            'partner_id': customer_id.id,
            'template_id': subscription_template_id.id,
            'company_id': sr_company_id,
            'uuid': str(uuid4())
        }

        subscription_id = subscription_obj.create(subscription_vals)

        return subscription_id
                
    def create_customer_delivery_address(self, customer_address_info, customer_info_detail, partner_id):
        _logger.info("--> create_customer_delivery_address")
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        if not self.company_id:
            self.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        country_id = False
        country = self.env['res.country'].search([('code','=','MX')])
        if country:
            country_id = country[0].id
        data_customer = {}
        data_customer.update({
                            'name' : customer_info_detail['firstName'] + ' ' + customer_info_detail['lastName'],
                            'street_name' : customer_address_info['addressLine1'],
                            'l10n_mx_edi_colony': customer_address_info['addressLine2'],
                            'city' : customer_address_info['city'],
                            'itl_state': customer_address_info['state'],
                            'zip' : customer_address_info['zip'],
                            'phone' : customer_info_detail['contactNumber'],
                            'email' : customer_info_detail['emailAddress'],
                            'company_type' : 'person',
                            'type': 'delivery',
                            'company_id': self.company_id.id,
                            'country_id': country_id,
                            'parent_id': partner_id.id
                            })
        _logger.info("--> data_customer: " + str(data_customer))
        #context = dict(self.env.context or {})
        customer_id = self.env['res.partner'].with_context({'from_api':True, 'status': 'success'}).create(data_customer)

        return customer_id


    def create_response_message(self, iccid_number=None):
        if not iccid_number:
            iccid_number = self.sale_subscription_id.iccid_number
        if iccid_number[-1] == 'F':
            iccid_number = iccid_number[:-1]
            self.sale_subscription_id.iccid_number = iccid_number
        self.response_message = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                                    <DispatchSimResponse>
                                        <status>success</status>
                                        <orderRefId>{0}</orderRefId>
                                        <iccid>{1}</iccid>
                                        <msisdn>{2}</msisdn>
                                        <subscriptionId>{3}</subscriptionId>
                                        <!--Reason can be either NewCustomer or ReplacementSIM depending on whether this is a new customer sign up
                                        or simply a lost/damaged/stolen SIM -->
                                        <reason>{4}</reason>
                                    </DispatchSimResponse>""".format(str(self.sale_subscription_id.order_ref_id), str(iccid_number), str(self.sale_subscription_id.msisdn_number), str(self.sale_subscription_id.subscription_id_ref), str(self.reason))
        self.response_message_status = 'new'
        
    
    def send_response_message_to_sr(self):
        result = self.env['sr.get.message'].send_message_to_queue(self.response_message)
        if result:
            self.response_message_status = 'done'
            self.message_post(body="El mensaje de respuesta se envió correctamente a Separate Reality.", subject="Registro procesado")
        else:
            self.response_message_status = 'error'
            self.message_post(body="El mensaje de respuesta no pudo ser enviado a Separate Reality.", subject="Registro procesado")

    def change_serial(self, sale_order_id, stock_quant):
        serie_id = self.env['stock.production.lot'].search([('name','=',stock_quant.lot_id.name),('product_qty','>',0)])
        if stock_quant.lot_id:
            #flag_error = False
            stock_picking_id = self.env['stock.picking'].search([('sale_id','=',sale_order_id.id)])
            if stock_picking_id:
                stock_picking_id = stock_picking_id[0]
                for stock_line in stock_picking_id.move_ids_without_package:
                    if len(stock_line.move_line_ids) > 0:
                        stock_line.move_line_ids[0].lot_id = stock_quant.lot_id
                        stock_line.move_line_ids[0].qty_done = 1
                        #_logger.info("-> adding new serie: " + str(stock_line.move_line_ids[0].lot_id))
                    else:
                        move_line_add = [(0, 0, {'product_uom_id': stock_line.product_uom.id,
                                                'picking_id': stock_line.picking_id.id,
                                                'move_id': stock_line.id,
                                                'product_id': stock_line.product_id.id,
                                                'location_id': stock_line.location_id.id,
                                            'lot_id': stock_quant.lot_id.id,
                                            'location_dest_id': stock_line.location_dest_id.id,
                                            'qty_done': 1})]
                        stock_line.move_line_ids = move_line_add
                        
                #if not flag_error:
                #_logger.info("-> No errors")
                stock_picking_id.action_assign()
                stock_picking_id.button_validate()

    def search_serial(self, iccid):
        stock_quant = self.env['stock.quant'].search([('location_id.usage','=', 'internal'),('lot_id.name','=',iccid),('quantity','>',0)])
        if stock_quant and len(stock_quant) > 0:
            return stock_quant[0]
        else:
            return False                
    
    def send_mail(self, invoice):
        template_id = self.env.ref('account.email_template_edi_invoice', False)
        #_logger.info("-> Sending mail")
        #_logger.info("-> template_id: " + str(template_id))
        if template_id:
            self.env['mail.template'].browse(template_id.id).send_mail(invoice.id, force_send=True)

        
    def create_customer(self, xml_doc, token_info, customer_id_ref):
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        if not self.company_id:
            self.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]

        customer_info = xml_doc['DoPlaceOrderEvent']['order']['accountAddItems']['item']['extendedData']
        exception_message = False
        if "\\" in str(customer_info):
            customer_info = str(customer_info).replace("\\",'')
        customer_info = json.loads(customer_info)
        customer_info_detail = customer_info['personalDetails']
        customer_address_info = customer_info['deliveryAddress']

        rfc_org = str(customer_info_detail['taxCode']) if 'taxCode' in customer_info_detail else ''
        is_valid_rfc = False
        if rfc_org not in ['XAXX010101000','XEXX010101000']:
            is_valid_rfc = self.env['res.partner'].validate_rfc(rfc_org)
        
        if is_valid_rfc:
            domain = ['|',('vat','=',rfc_org),('customer_id_ref','=',customer_id_ref)]
        else:
            domain = [('customer_id_ref','=',customer_id_ref)]
        
        customer_id = self.env['res.partner'].search(domain)
        
        if not customer_id:
            data_customer = {}
            if token_info and 'token' in token_info and 'card' in token_info and token_info['card'] != 'false':
                token_data = {'cardToken': token_info['token'],
                        'cardType': token_info['cardType']
                }
                token_ids = [(0, 0 , token_data)]
                data_customer.update({'token_ids': token_ids})
            #else:
            #    exception_message = "No se agregó información del token del cliente"

            # For avoid send email
            #email = str(customer_info_detail['emailAddress']).replace('@','')
            email = str(customer_info_detail['emailAddress'])
            
            if is_valid_rfc:
                data_customer.update({'vat': rfc_org})
            else:
                data_customer.update({'vat_invalid': rfc_org})
            country_id = False
            country = self.env['res.country'].search([('code','=','MX')])
            if country:
                country_id = country[0].id
            data_customer.update({
                            'name' : customer_info_detail['firstName'] + ' ' + customer_info_detail['lastName'],
                            'street_name' : customer_address_info['addressLine1'],
                            'l10n_mx_edi_colony': customer_address_info['addressLine2'],
                            'city' : customer_address_info['city'],
                            'itl_state': customer_address_info['state'],
                            'zip' : customer_address_info['zip'],
                            'phone' : customer_info_detail['contactNumber'],
                            'email' : email,
                            'customer_id_ref': customer_id_ref,
                            'company_type' : 'person',
                            'company_id': self.company_id.id,
                            'country_id': country_id
                            })

            #context = dict(self.env.context or {})
            customer_id = self.env['res.partner'].with_context({'from_api':True, 'status': 'success'}).create(data_customer)

        return customer_id, exception_message

    def create_subscription_template(self, plan_info):
        plan_items = []
        plan_items.append(plan_info['description'])
        plan_items.append(plan_info['billingMode'])
        plan_items.append(str(plan_info['recurringFrequency']) + " " + str(plan_info['recurringFrequencyUnit']))
        plan_items.append(str(plan_info['validity']) + " " + str(plan_info['validityUnit']))

        plan_description = '\n'.join(plan_items)

        data_subscription_template = {
            'code': plan_info['productLegacyId'],
            'name': plan_info['productName'],
            'description': plan_description
        }

        subscription_template_id = self.env['sale.subscription.template'].create(data_subscription_template)

        return subscription_template_id
    
    def create_product_subscription(self, product_info, subscription_template_id, product_category, is_rokit):
        product_items = []
        if product_category == 'plan' and not is_rokit:
            product_items.append(product_info['description'])
            product_items.append(str(product_info['localMinutes']) + " " + str(product_info['localMinutesUnit']))
            product_items.append(str(product_info['localSMS']) + " " + str(product_info['localSMSUnit']))
            product_items.append(str(product_info['localData']) + " " + str(product_info['localDataUnit']))
        if product_category == 'addOn' or is_rokit:
            product_items.append(product_info['description'])
            product_items.append(str(product_info['validity']) + " " + str(product_info['validityUnit']))

        description = '\n'.join(product_items)
        
        sat_code = self.env['l10n_mx_edi.product.sat.code'].search([('code','=','81161700')])
        sat_code_id = False
        if sat_code:
            sat_code_id = sat_code.id
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        if not self.company_id:
            self.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        sr_tax_id = self.company_id.sr_tax_id
        price = float(product_info['upfrontCost']) / 100
        untaxed_price = price / 1.16

        isRecurring = False
        if product_info['recurring'] == 'true':
            isRecurring = True
        data_product = {
            'name': product_info['productName'],
            'description_sale': description,
            'list_price': untaxed_price,
            'type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
            'subscription_template_id': subscription_template_id.id,
            'recurring_invoice': True,
            'productLegacyId': product_info['productLegacyId'],
            'isRecurring': isRecurring,
            'productCategory': product_category,
            'l10n_mx_edi_code_sat_id': sat_code_id,
            'taxes_id': [(6, 0, [sr_tax_id.id])]
        }

        product_id = self.env['product.product'].create(data_product)
        return product_id

    def create_sale_order(self, customer_id, product_id, iccid, total_amount):
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        if not self.company_id:
            self.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        sale_order = self.env['sale.order']
        sim_product_id = self.company_id.sr_sim_product_id
        sr_warehouse_id = self.company_id.sr_warehouse_id
        sr_carrier_id = self.company_id.sr_carrier_id

        order_lines = []
        data_sale = {}
        
        if sr_warehouse_id:
            data_sale.update({'warehouse_id': sr_warehouse_id.id})
            if sr_warehouse_id.operating_unit_id:
                data_sale.update({'operating_unit_id': sr_warehouse_id.operating_unit_id.id})
        if not iccid:
            if sim_product_id:
                order_lines.append((0, 0, {'product_id': sim_product_id.id, 'price_unit': 0.1}))
            if sr_carrier_id:
                data_sale.update({'carrier_id': sr_carrier_id.id})
        #if warehouse_id:
        #    data_sale.update({'warehouse_id': warehouse_id.id})
        total_amount = float(total_amount) / 100
        total_untaxed_amount = float(total_amount) / 1.16

        if not iccid:
            total_untaxed_amount = total_untaxed_amount - 0.1

        #if total_amount == 0.0:
        #    total_untaxed_amount = 0.1
        sr_tax_id = self.company_id.sr_tax_id

        product_id = product_id.with_context(lang='es_MX')
        name = self.env['sale.order.line'].get_sale_order_line_multiline_description_sale(product_id)
        order_lines.append((0, 0, {'product_id': product_id.id, 'name': name, 'product_uom_qty': 1, 'price_unit': total_untaxed_amount, 'discount': 0}))

        data_sale.update({
            'partner_id': customer_id.id,
            'order_line': order_lines,
            'company_id': self.company_id.id,
            'team_id': False,
        })
        _logger.info("-> data_sale: " + str(data_sale))
        #raise ValidationError("Testing...")
        sale_order_id = sale_order.create(data_sale)
        if sale_order_id.carrier_id and sale_order_id.carrier_id.delivery_type == '_99minutos':
            sale_order_id.get_delivery_price()
            #if sale_order_id.delivery_rating_success:
            #    sale_order_id.set_delivery_line()

        return sale_order_id
    
    def create_invoice(self, sale_order_id):
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        if not self.company_id:
            self.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]

        sr_warehouse_id = self.company_id.sr_warehouse_id
        operating_unit = sr_warehouse_id.operating_unit_id
        if not sr_warehouse_id:
            sr_warehouse_id = 1
        invoice_id = sale_order_id.with_context({'default_warehouse_id': sr_warehouse_id, 'default_company_id': sr_company_id, 'force_company': sr_company_id, 'default_operating_unit_id': operating_unit.id, 'default_user_id': False}).action_invoice_create()[0]
        invoice_id = self.env['account.invoice'].browse(invoice_id)
        invoice_id.user_id = False

        return invoice_id
    
    def create_payment(self, invoice):
        """
        Crea pago para la factura indicada
        """
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        if not self.company_id:
            self.company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        
        sr_payment_journal_id = self.company_id.sr_payment_journal_id
        if not sr_payment_journal_id:
            raise ValidationError("No se econtró el diario de pago de factura.")

        payment_type = 'inbound' if invoice.type in ('out_invoice', 'in_refund') else 'outbound'
        if payment_type == 'inbound':
            payment_method = self.env.ref('account.account_payment_method_manual_in')
        else:
            payment_method = self.env.ref('account.account_payment_method_manual_out')

        AccountPayment = self.env['account.payment']
        AccountRegisterPayments = self.env['account.register.payments']
        
        vals = {
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': sr_payment_journal_id.id,
                'payment_type': payment_type,
                'payment_method_id': payment_method.id,
                'group_invoices': False,
                'invoice_ids': [(6, 0, [invoice.id])],
                'multi': False,
                'payment_date': invoice.date_invoice,
                'communication': invoice.name
            }

        account_register_payment_id = AccountRegisterPayments.with_context({'active_ids': [invoice.id, ]}).create(vals)
        payment_vals = account_register_payment_id.get_payments_vals()

        return AccountPayment.create(payment_vals)

    def reload_xml_message(self):
        _logger.info("---> reload_xml_message")
        for record in self:
            xml_doc = xmltodict.parse(record.xml_message)
            _logger.info("---> after xmltodict.parse")
            if 'DoPlaceServiceOrderEvent' in xml_doc:
                DoPlaceServiceOrderEvent = xml_doc['DoPlaceServiceOrderEvent']
                messageID = DoPlaceServiceOrderEvent['messageID']
                record.message_id = messageID

                if 'service' in DoPlaceServiceOrderEvent:
                    service_source = DoPlaceServiceOrderEvent['service']['@source']
                    record.service_source = service_source
                if DoPlaceServiceOrderEvent['addItems'] == None:
                    record.product_category = 'other'
                order_event = self.search([('name','ilike','DoPlaceOrderEvent'),('order_ref_id','=',messageID)])
                
                if order_event:
                    _logger.info("---> Entro")
                    record.already_processed = True
            if 'DoPlaceOrderEvent' in xml_doc:
                _logger.info("---> Entró reload DoPlaceOrderEvent")
                DoPlaceOrderEvent = xml_doc['DoPlaceOrderEvent']
                _logger.info("---> After get xml_doc['DoPlaceOrderEvent']")
                messageID = DoPlaceOrderEvent['messageID']
                _logger.info("---> After get DoPlaceOrderEvent['messageID']")
                record.message_id = messageID
