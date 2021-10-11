# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from urllib.request import urlopen
import urllib
import requests
import json
import base64
import pytz
from pytz import timezone


import logging
_logger = logging.getLogger(__name__)


class ItlRequests(models.Model):
    _name = "itl.request"
    _inherit = ['mail.thread']
    _rec_name = "id"
    
    def _get_pfx_b64(self, company=None):
        if not company:
            company = self.env.user.company_id
        pfx_file = company.pfx_file or False
        
        if pfx_file:
            return pfx_file
    
    def _get_usuario_pade(self, company=None):
        if not company:
            company = self.env.user.company_id
        user_name = company.l10n_mx_edi_pac_username
        if user_name:
            return user_name
    
    def _get_pass_pade(self, company=None):
        if not company:
            company = self.env.user.company_id
        password = company.l10n_mx_edi_pac_password
        if password:
            return password
        
    def _get_password_pfx(self, company=None):
        if not company:
            company = self.env.user.company_id
        password_pfx = company.password_pfx or False
        
        if password_pfx:
            return password_pfx
    
    def _get_contrato(self, company=None):
        if not company:
            company = self.env.user.company_id
        contrato = company.contrato or False
        
        if contrato:
            return contrato
    
    company_id = fields.Many2one('res.company', string='Company',  default=lambda self: self.env.user.company_id)
    # Request inicial
    tipoFactura = fields.Selection([('cliente','Cliente'),('proveedor','Proveedor')], string="Tipo de factura", required=True)
    rfcEmisor = fields.Char(string="RFC Emisor")
    rfcReceptor = fields.Char(string="RFC Receptor")
    rfcSolicitante = fields.Char(string="RFC Solicitante", required=True, default=lambda self: self.env.user.company_id.vat)
    fechaInicio = fields.Datetime(string="Fecha inicio", required=True, default=fields.Datetime.today)
    fechaFinal = fields.Datetime(string="Fecha final", required=True, default=fields.Datetime.today)
    tipoSolicitud = fields.Selection([('CFDI','CFDI'),('Metadata','Metadata')], string="Tipo de solicitud", required=True)
    pfx = fields.Text(string="PFX (base64)", required=True, default=_get_pfx_b64)
    password = fields.Char(string="Contraseña PFX", required=True, default=_get_password_pfx)
    usuario = fields.Char(string="Usuario PADE", required=True, default=_get_usuario_pade)
    passPade = fields.Char(string="Contraseña PADE", required=True, default=_get_pass_pade)
    contrato = fields.Char(string="Contrato", required=True, default=_get_contrato)
    numeroSolicitud = fields.Char(string="Número de solicitud", copy=False)
    response_ids = fields.One2many('itl.response', 'id_request', string="Responses", copy=False)
    status = fields.Selection([('nueva','Nueva'),('generada','Generada'),('lista','Lista'),('terminada','Terminada')], string="Estado", default='nueva', copy=False)
    invoice_ids = fields.Char(string="Invoice ids", copy=False)
    
    
    @api.onchange('tipoFactura')
    def _onchnage_tipoFactura(self):
        if self.tipoFactura:
            if self.tipoFactura == 'cliente':
                self.rfcEmisor = self.env.user.company_id.vat
                self.rfcReceptor = False
            if self.tipoFactura == 'proveedor':
                self.rfcReceptor = self.env.user.company_id.vat
                self.rfcEmisor = False
    
    def nueva_solicitud(self):
        for company in self.env['res.company'].search([]):
        
            active_cliente = company.active_cliente
            active_proveedor = company.active_proveedor
            
            if active_cliente:
                _logger.info("--> nueva_solicitud cliente")
                self.crear_solicitud('cliente', company)
            if active_proveedor:
                _logger.info("--> nueva_solicitud proveedor")
                self.crear_solicitud('proveedor', company)
    
    def crear_solicitud(self, tipoFactura=None, company=None):
        if not company:
            company = self.env.user.company_id
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_tz = pytz.UTC.localize(datetime.strptime(str(fields.Datetime.now()), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(timezone('America/Mexico_City'))
        
        only_date = date_tz.strftime("%Y-%m-%d")
        
        local = pytz.timezone ("America/Mexico_City")
        combineInicio = datetime.strptime(only_date + str('T00:00:02'), '%Y-%m-%dT%H:%M:%S')
        local_dt = local.localize(combineInicio, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        fechaInicio = datetime.strftime(utc_dt - timedelta(1), '%Y-%m-%dT%H:%M:%S')
        
        combineFin = datetime.strptime(only_date + str('T23:59:58'), '%Y-%m-%dT%H:%M:%S')
        local_dt = local.localize(combineFin, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        fechaFinal = datetime.strftime(utc_dt - timedelta(1), '%Y-%m-%dT%H:%M:%S')
        
        params = {
            "rfcSolicitante": company.vat,
            "fechaInicio": fechaInicio,
            "fechaFinal": fechaFinal,
            "tipoSolicitud": 'CFDI',
            "pfx": self._get_pfx_b64(company),
            "password": self._get_password_pfx(company),
            "usuario": self._get_usuario_pade(company),
            "passPade": self._get_pass_pade(company),
            "contrato": self._get_contrato(company),
            "status": 'nueva',
            "company_id": company.id
        }
        
        if tipoFactura:
            if tipoFactura == 'cliente':
                if company.vat:
                    params.update({"rfcEmisor": company.vat,
                                  "tipoFactura": tipoFactura})
            if tipoFactura == 'proveedor':
                if company.vat:
                    params.update({"rfcReceptor": company.vat,
                                  "tipoFactura": tipoFactura})
        else:
            if self.tipoFactura == 'cliente':
                if company.vat:
                    params.update({"rfcEmisor": company.vat})
            if self.tipoFactura == 'proveedor':
                if company.vat:
                    params.update({"rfcReceptor": company.vat})
        
        res = all(params.values())
        if not res:
            _logger.info(str("Hay algunos campos vacíos en el cuerpo de la solicitud."))
            self.message_post(body="Solicitud no generada. Hay algunos campos vacíos en el cuerpo de la solicitud.", subject="Error al generar la solicitud")
            _logger.info(str(params))
        else:
            #_logger.info(str("Cuerpo de la solicitud"))
            record = self.sudo().create(params)
            _logger.info(str("Registro creado"))
            record.generar_solicitud()
            
    
    def generar_solicitud(self):
        if self.status == 'nueva':
            self.validations()
            ICPSudo = self.env['ir.config_parameter'].sudo()
            url_solicitud = ICPSudo.get_param('itl_descarga_masiva.url_solicitud') or False
            
            #convert the date string into object 
            fechaInicio = self.fechaInicio.strftime("%Y-%m-%dT%H:%M:%S")
            utc_start_date = datetime.strptime(fechaInicio,"%Y-%m-%dT%H:%M:%S")
            fechaInicio = utc_start_date.astimezone(timezone('America/Mexico_City'))
            fechaInicio = fechaInicio.strftime("%Y-%m-%dT%H:%M:%S")

            fechaFinal = self.fechaFinal.strftime("%Y-%m-%dT%H:%M:%S")
            utc_end_date = datetime.strptime(fechaFinal,"%Y-%m-%dT%H:%M:%S")
            fechaFinal = utc_end_date.astimezone(timezone('America/Mexico_City'))
            fechaFinal = fechaFinal.strftime("%Y-%m-%dT%H:%M:%S")

            params = {
                "rfcSolicitante": self.rfcSolicitante,
                "fechaInicio": fechaInicio,
                "fechaFinal": fechaFinal,
                "tipoSolicitud": self.tipoSolicitud,
                "pfx": self.pfx,
                "password": self.password,
                "usuario": self.usuario,
                "passPade": self.passPade,
                "contrato": self.contrato,
            }
            _logger.info("params: " + str(params))
            #raise ValidationError("Testing 2...")
            if self.tipoFactura == 'cliente':
                if self.company_id.vat:
                    params.update({"rfcEmisor": self.rfcEmisor})
            if self.tipoFactura == 'proveedor':
                if self.company_id.vat:
                    params.update({"rfcReceptor": self.rfcReceptor})

            _logger.info(str(params))
            #raise ValidationError("Testing...")
            headers = {'Content-type': 'application/json'}
            try:
                _logger.info("url_solicitud: " + str(url_solicitud))
                _logger.info("data: " + str(json.dumps(params)))
                _logger.info("headers: " + str(headers))
                r = requests.post(url_solicitud, data=json.dumps(params),  headers=headers, verify=False)
                data = r.json() 
                #raise ValidationError(str(data))
                values = {
                    'id_request': self.id,
                    'company_id': self.company_id.id
                }
                _logger.info("data: " + str(data))
                flag_error = False
                if 'numeroSolicitud' in data:
                    values.update(
                        {'numeroSolicitud': data['numeroSolicitud'],
                         'estadoSolicitud': data['estadoSolicitud'],
                         'mensaje': data['mensaje'][0]
                        })
                    if data['numeroSolicitud'] != "0":
                        self.numeroSolicitud = data['numeroSolicitud']
                        self.status = 'generada'
                    else:
                        self.message_post(body="Solicitud no generada. " + str(data['mensaje'][0]), subject="Solicitud no generada")
                        flag_error = True
                    if 'respuestaSAT' in data:
                        values.update({'respuestaSAT': data['respuestaSAT']})
                if 'apierror' in data:
                    values.update({
                        'estadoSolicitud': data['status'],
                        'mensaje': data['message'] + " código: " + str(data['codigo'])
                    })

                self.response_ids = [(0, 0, values)]
                if self.tipoFactura == 'cliente' and not flag_error:
                    self.message_post(body="Solicitud para descarga de facturas de cliente generada correctamente.", subject="Solicitud generada")
                if self.tipoFactura == 'proveedor' and not flag_error:
                    self.message_post(body="Solicitud para descarga de facturas de proveedor generada correctamente.", subject="Solicitud generada")
            except requests.exceptions.RequestException as e:
                self.message_post(body="Ocurrió un error en la llamada a la API que genera la solicitud. " + str(e), subject="Error en llamada a API")
            
    def revisa_solicitudes(self):
        _logger.info(str("---> Revisando el estado de las solicitudes"))
        company_ids = self.env['res.company'].sudo().search([])
        for company in company_ids:
            _logger.info("---> Revisando solicitudes de " + str(company.name))
            solicitudes = self.sudo().search([('status','in',['generada','lista']),('company_id','=',company.id)])
            _logger.info(str("---> Total de solicitudes: " + str(len(solicitudes))))
            if solicitudes:
                for solicitud in solicitudes:
                    solicitud.estado_solicitud()
                _logger.info(str("Fin de la revisión"))
            else:
                _logger.info(str("Ninguna solicitud por revisar"))
    
    def estado_solicitud(self):
        if self.status in ['generada','terminada','lista']:
            _logger.info(str("Solicitud #: " + str(self.id)))
            ICPSudo = self.env['ir.config_parameter'].sudo()
            url_estatus = ICPSudo.get_param('itl_descarga_masiva.url_estatus') or False

            params = {
                "numeroSolicitud": self.numeroSolicitud,
                "usuario": self.usuario,
                "passPade": self.passPade,
                "contrato": self.contrato,
            }

            headers = {'Content-type': 'application/json'}
            try:
                r = requests.post(url_estatus, data=json.dumps(params), headers=headers, verify=False)

                data = r.json() 

                values = {
                    'id_request': self.id
                }

                if 'numeroSolicitud' in data:
                    values.update(
                        {'numeroSolicitud': data['numeroSolicitud'],
                         'estadoSolicitud': data['estadoSolicitud'],
                         'mensaje': data['mensaje'][0]
                        })
                    if 'paquetes' in data:
                        values.update({'paquetes': data['paquetes'][0]})
                        self.status = 'lista'
                        self.response_ids = [(0, 0, values)]
                        self.message_post(body="Paquetes listos para descargar.", subject="Descarga lista")
                        self.obtener_paquetes()
                    elif 'estadoSolicitud' in data and data['estadoSolicitud'] in ["5","0"]:
                        self.status = 'terminada'
                        self.response_ids = [(0, 0, values)]
                    else:
                        self.response_ids = [(0, 0, values)]
            except requests.exceptions.RequestException as e:
                self.message_post(body="Ocurrió un error en la llamada a la API que obtiene el estado de la solicitud. " + str(e), subject="Error en llamada a API")

            
    def obtener_paquetes(self):
        if self.response_ids:
            responses = self.response_ids.filtered(lambda r: r.estadoSolicitud == "7" and r.paquetes)
            if responses:
                _logger.info(str("Paquetes URL: " + str(responses[-1].paquetes)))
                try:
                    _logger.info("Descargando paquetes...")
                    paquetes = urlopen(responses[-1].paquetes).read()
                    paquetes_b64_encoded = base64.b64encode(paquetes)
                    paquetes_b64 = paquetes_b64_encoded.decode('utf-8')
                    _logger.info("Paquetes descargados...")
                    if self.tipoSolicitud == 'CFDI':
                        self.importar_facturas(paquetes_b64)
                    else:
                        filename = responses[-1].paquetes.split('?')[0].split('/')[-1] + ".zip"
                        self.attach_to_solicitud(self, paquetes_b64_encoded, filename)
                        self.message_post(body="Archivo de metadatos descargado y adjuntado correctamente.", subject="Archivo de metadata listo")
                        self.status = 'terminada'
                    
                except urllib.error.URLError as e:
                    self.message_post(body="Error durante la descarga: " + str(e.reason) + " code: " + str(e.code), subject="Error en descarga")
                    _logger.info("Error durante la descarga: " + str(e.reason) + " code: " + str(e.code))
    
    def attach_to_solicitud(self, solicitud, zip_file, paquete_name):
        sub_values = {
            'res_model': 'itl.request',
            'res_id': solicitud.id,
            #'name': invoice.l10n_mx_edi_cfdi_name,
            'name': paquete_name,
            'datas': zip_file,
            #'datas_fname': xml_name,
        }
        IrAttachment = self.env['ir.attachment']
        
        attachment = IrAttachment.create(sub_values)
        
        return attachment
    
    def get_raw_file(self, paquetes_b64):
        '''Convertir archivo binario a byte string.'''
        return base64.b64decode(paquetes_b64)
    
    def ver_invoices(self):
        if self.tipoFactura == 'cliente':
            view = 'account.action_invoice_tree1'
        else:
            view = 'account.action_vendor_bill_template'
        #view = 'account.action_invoice_tree2'
        action = self.env.ref(view).read()[0]
        invoice_ids = json.loads(self.invoice_ids)
        action['domain'] = [('id', 'in', invoice_ids)]
        return action  
                    
    def importar_facturas(self, paquetes):
        import_obj = self.env['xml.to.invoice']
        
        #Config for client
        cuenta_cobrar_cliente_id = self.company_id.cuenta_cobrar_cliente_id
        invoice_status_customer = self.company_id.invoice_status_customer or False
        user_customer_id = self.company_id.user_customer_id
        team_customer_id = self.company_id.team_customer_id
        journal_customer_id = self.company_id.journal_customer_id
        cuenta_ingreso_cliente_id = self.company_id.cuenta_ingreso_cliente_id
        
        #Config for provider
        cuenta_pagar_proveedor_id = self.company_id.cuenta_pagar_proveedor_id
        invoice_status_provider = self.company_id.invoice_status_provider or False
        warehouse_provider_id = self.company_id.warehouse_provider_id
        journal_provider_id = self.company_id.journal_provider_id
        user_provider_id = self.company_id.user_provider_id
        cuenta_gasto_proveedor_id = self.company_id.cuenta_gasto_proveedor_id
        
        vals = {
            'cuenta_cobrar_cliente_id': cuenta_cobrar_cliente_id.id,
            'cuenta_ingreso_cliente_id': cuenta_ingreso_cliente_id.id,
            'invoice_status_customer': invoice_status_customer,
            'user_customer_id': user_customer_id.id,
            'team_customer_id': team_customer_id.id,
            'journal_customer_id': journal_customer_id.id,
            'cuenta_pagar_proveedor_id': cuenta_pagar_proveedor_id.id,
            'cuenta_gasto_proveedor_id': cuenta_gasto_proveedor_id.id,
            'invoice_status_provider': invoice_status_provider,
            'warehouse_provider_id': warehouse_provider_id.id,
            'journal_provider_id': journal_provider_id.id,
            'user_provider_id': user_provider_id.id,
            'company_id': self.company_id.id,
            'uploaded_file': paquetes
        }
        record = import_obj.create(vals)
        
        invoice_ids, mensaje2 = record.validate_bills_downloaded()
        
        if invoice_ids:
            self.invoice_ids = invoice_ids
            self.message_post(body="Facturas descargadas e importadas correctamente.", subject="Importación correcta")
            
        if mensaje2:
            self.message_post(body=mensaje2, subject="Log de importación")
        
        self.status = 'terminada'
    
    def get_raw_file(self, pfx_file):
        '''Convertir archivo binario a byte string.'''
        return base64.b64decode(pfx_file)

    def validations(self):
        if self.tipoFactura == 'cliente':
            if not self.rfcEmisor:
                self.message_post(body="No se ha establecido el RFC de la compañía", subject="Problema con RFC")
        if self.tipoFactura == 'proveedor':
            if not self.rfcReceptor:
                self.message_post(body="No se ha establecido el RFC de la compañía", subject="Problema con RFC")
        if not self.pfx:
            self.message_post(body="Debe de colocar el archivo PFX en la configuración", subject="Problema con archivo PFX")
        if self.fechaInicio > self.fechaFinal:
            self.message_post(body="El rango de fechas es incorrecto", subject="Problema con fechas")
            
    
class ItlResponse(models.Model):
    _name = "itl.response"
    
    id_request = fields.Many2one('itl.request', string="Request", ondelete='cascade')

    numeroSolicitud = fields.Char(string="Número de solicitud")
    estadoSolicitud = fields.Char(string="Estado de la solicitud")
    mensaje = fields.Char(string="Mensaje")
    respuestaSAT = fields.Char(string="Respuesta SAT")
    paquetes = fields.Char(string="Paquetes")
    
    company_id = fields.Many2one('res.company', string='Company',  default=lambda self: self.env.user.company_id)