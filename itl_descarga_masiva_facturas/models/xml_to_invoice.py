
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
# from xml.sax.saxutils import escape
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import xmltodict

import base64
import calendar
import zipfile
import io
from suds.client import Client
import random
import pdb

import logging
_logger = logging.getLogger(__name__)

class XmlToInvoice(models.TransientModel):
    _name = 'xml.to.invoice'
    
    # Originals fields
    company_id = fields.Many2one('res.company', 'Company',
        default=lambda self: self.env.user.company_id.id,
        required=True)
    filename = fields.Char(string='Nombre archivo')
    uploaded_file = fields.Binary(string='Facturas',
        required=True)
    import_type = fields.Selection(
        [('start_amount','Saldos Iniciales'),
        ('regular','Factura regular')],
        string='Tipo de Importacion',
        required=True,
        default='regular')
    line_analytic_tag_ids = fields.Many2many('account.analytic.tag', 
        string='Etiquetas analiticas',
        required=False)
    team_id = fields.Many2one('crm.team',
        string='Equipo de ventas',)
    user_id = fields.Many2one('res.users',
        string='Comercial',)
    line_analytic_account_id = fields.Many2one('account.analytic.account', 
        string='Cuenta analitica de linea',
        required=False)
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Plazo de pago',
        help='Se utilizara este plazo de pago para las empresas creadas automaticamente, '+\
        '\n si no se especifica, se usara el de 15 dias'
        )


    sat_validation = fields.Boolean(string='Validar en SAT',
                                    default=False)
    invoice_type = fields.Selection(
        [('out_invoice', 'Cliente'),
         ('in_invoice', 'Proveedor')],
        string='Tipo de factura',
        required=False,
        default=False)
    line_account_id = fields.Many2one('account.account',
                                      string='Cuenta de linea',
                                      required=False,
                                      help='Si la empresa no tiene definida una cuenta de importacion xml por defecto, se usara esta')
    invoice_account_id = fields.Many2one('account.account',
                                         string='Cuenta de Factura',
                                         required=False)
    journal_id = fields.Many2one('account.journal',
                                 string='Diario',
                                 required=False)
    payment_journal_id = fields.Many2one('account.journal',
                                         string='Banco de pago', required=False, domain="[('type','=','bank')]")
    
    ### Cliente ##########################################
    cuenta_cobrar_cliente_id = fields.Many2one('account.account',
                                               string='Cuenta por Cobrar Clientes',
                                               required=True, default=lambda self: self.env['account.account'].search(
            [('code', '=', '105.01.001'), ('company_id', '=', self.env.user.company_id.id)]))
    cuenta_ingreso_cliente_id = fields.Many2one('account.account',
                                                string='Cuenta de Ingresos Clientes',
                                                required=False, default=lambda self: self.env['account.account'].search(
            [('code', '=', '401.01.001'), ('company_id', '=', self.env.user.company_id.id)]))
    #line_analytic_account_customer_id = fields.Many2one('account.analytic.account',
    #                                                    string='Cuenta analitica de linea',
    #                                                    required=False)
    payment_term_customer_id = fields.Many2one(
        'account.payment.term',
        string='Plazo de pago',
        help='Se utilizara este plazo de pago para las empresas creadas automaticamente, ' + \
             '\n si no se especifica, se usara el de 15 dias'
    )
    user_customer_id = fields.Many2one('res.users',
                                       string='Representante Comercial')
    team_customer_id = fields.Many2one('crm.team',
                                       string='Equipo de ventas')
    warehouse_customer_id = fields.Many2one('stock.warehouse', string='Almacén',
                                            help='Necesario para crear el mov. de almacén')
    journal_customer_id = fields.Many2one('account.journal',
                                          string='Diario Clientes',
                                          required=False, default=lambda self: self.env['account.journal'].search(
            [('name', '=', 'Customer Invoices'), ('company_id', '=', self.env.user.company_id.id)]))
    payment_journal_customer_id = fields.Many2one('account.journal',
                                                  string='Banco de pago', domain="[('type','=','bank')]")
    line_analytic_tag_customer_ids = fields.Many2many('account.analytic.tag','line_analytic_customer',
                                                      string='Etiquetas analíticas',
                                                      required=False)
    invoice_status_customer = fields.Selection([('draft', 'Borrador'), ('abierta', 'Abierta'), ('pagada', 'Pagada')],
                                               string='Subir en estatus')
    invoice_payment_type_customer = fields.Selection(
        [('fecha_factura', 'Con  la misma fecha de la factura'), ('fecha_fin_mes', 'Con la fecha de final del mes'),
         ('fecha_especifica', 'Con alguna fecha específica')], string='Fecha de pago')
    invoice_date_customer = fields.Date(string='Fecha')
    payment_method_customer = fields.Many2one('l10n_mx_edi.payment.method', string='Forma de pago')
    usage_customer = fields.Selection([
        ('G01', 'Adquisición de mercancías'),
        ('G02', 'Devoluciones, descuentos o bonificaciones'),
        ('G03', 'Gastos en general'),
        ('I01', 'Construcciones'),
        ('I02', 'Mobilario y equipo de oficina por inversiones'),
        ('I03', 'Equipo de transporte'),
        ('I04', 'Equipo de cómputo y accesorios'),
        ('I05', 'Dados, troqueles, moldes, matrices y herramental'),
        ('I06', 'Comunicaciones telefónicas'),
        ('I07', 'Comunicaciones satelitales'),
        ('I08', 'Otra maquinaria y equipo'),
        ('D01', 'Honorarios médicos, dentales y gastos hospitalarios'),
        ('D02', 'Gastos médicos por incapacidad o discapacidad'),
        ('D03', 'Gastos funerales'),
        ('D04', 'Donativos'),
        ('D05', 'Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)'),
        ('D06', 'Aportaciones voluntarias al SAR'),
        ('D07', 'Primas por seguros de gastos médicos'),
        ('D08', 'Gastos de transportación escolar obligatoria'),
        ('D09', 'Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones'),
        ('D10', 'Pagos por servicios educativos (colegiaturas)'),
        ('P01', 'Por definir'),
    ], 'Uso', default='P01',
        help='Used in CFDI 3.3 to express the key to the usage that will '
             'gives the receiver to this invoice. This value is defined by the '
             'customer. \nNote: It is not cause for cancellation if the key set is '
             'not the usage that will give the receiver of the document.')

    ### Proveedor #############################
    cuenta_pagar_proveedor_id = fields.Many2one('account.account',
                                                string='Cuenta por Pagar Proveedores',
                                                default=lambda self: self.env['account.account'].search(
            [('code', '=', '201.01.001'), ('company_id', '=', self.env.user.company_id.id)]))
    cuenta_gasto_proveedor_id = fields.Many2one('account.account',
                                                string='Cuenta de Gastos de Proveedor',
                                                default=lambda self: self.env['account.account'].search(
            [('code', '=', '601.84.001'), ('company_id', '=', self.env.user.company_id.id)]))
    line_analytic_account_provider_id = fields.Many2one('account.analytic.account',
                                                        string='Etiquetas analíticas', required=False)
    payment_term_provider_id = fields.Many2one(
        'account.payment.term',
        string='Plazo de pago',
        help='Se utilizara este plazo de pago para las empresas creadas automaticamente, ' + \
             '\n si no se especifica, se usara el de 15 dias'
    )
    user_provider_id = fields.Many2one('res.users',
                                       string='Comprador', )
    warehouse_provider_id = fields.Many2one('stock.warehouse', string='Almacén',
                                            help='Necesario para crear el mov. de almacén', required=False)
    journal_provider_id = fields.Many2one('account.journal',
                                          string='Diario Proveedores',
                                          default=lambda self: self.env['account.journal'].search(
            [('name', '=', 'Vendor Bills'), ('company_id', '=', self.env.user.company_id.id)]))
    payment_journal_provider_id = fields.Many2one('account.journal',
                                                  string='Banco de pago', domain="[('type','=','bank')]")
    line_analytic_tag_provider_ids = fields.Many2many('account.analytic.tag','line_analytic_provider',
                                                      string='Etiquetas analíticas',
                                                      required=False)
    invoice_status_provider = fields.Selection([('draft', 'Borrador'), ('abierta', 'Abierta'), ('pagada', 'Pagada')],
                                               string='Subir en estatus', required=False)
    invoice_payment_type_provider = fields.Selection(
        [('fecha_factura', 'Con  la misma fecha de la factura'), ('fecha_fin_mes', 'Con la fecha de final del mes'),
         ('fecha_especifica', 'Con alguna fecha específica')], string='Fecha de pago')
    invoice_date_provider = fields.Date(string='Fecha')

    ##############################
    
    def validate_bills_downloaded(self):
        '''
            Función principal. Controla todo el flujo de
            importación al clickear el botón (parsea el archivo
            subido, lo valida, obtener datos de la factura y
            guardarla crea factura en estado de borrador).
        '''

        raw_file = self.get_raw_file()
        zip_file = self.get_zip_file(raw_file)

        if zip_file:

            # extraer archivos dentro del .zip
            bills = self.get_xml_from_zip(zip_file)
            #raise ValidationError(str(bills))
        else:
            bills = self.get_xml_data(raw_file)
        
        valid_bills = []
        invalid_bills = []
        for bill in bills:
            mensaje = self.validations(bill)
            if mensaje:
                invalid_bills.append(mensaje)
                continue
            #raise ValidationError('ccccc')
            invoice, invoice_line, version, invoice_type, bank_id = self.prepare_invoice_data(bill)

            bill['bank_id'] = bank_id
            bill['invoice_type'] = invoice_type
            bill['invoice_data'] = invoice
            bill['invoice_line_data'] = invoice_line
            bill['version'] = version
            bill['valid'] = True

            mensaje = self.validations(bill)
            if mensaje:
                invalid_bills.append(mensaje)
                continue

            valid_bills.append(bill)

        # si todos son válidos, extraer datos del XML
        # y crear factura como borrador
        invoice_ids = []
        invoices_no_created = []
        warning_bills = []
        mensaje3 = ''
        for bill in valid_bills:
            invoice = bill['invoice_data']
            invoice_line = bill['invoice_line_data']
            invoice_type = bill['invoice_type']
            version = bill['version']
            
            if invoice_type == 'out_invoice' or invoice_type == 'out_refund':
                #_logger.info("invoice: " + str(invoice))
                draft, mensaje = self.create_bill_draft(invoice, invoice_line, invoice_type)
            else:
                draft, mensaje = self.create_bill_draft_vendor(invoice, invoice_line, invoice_type)

            draft.compute_taxes()
            #_logger.info("invoice amount_untaxed: " +str(invoice['amount_untaxed']))
            #_logger.info("invoice amount_tax: " +str(invoice['amount_tax']))
            #_logger.info("invoice amount_total: " +str(invoice['amount_total']))
            
            #amount_dif = 0
            #_logger.info("draft.amount_total: " + str(draft.amount_total) + " != invoice['amount_total']: " + str(float(invoice['amount_total'])))
            #if draft.amount_total != float(invoice['amount_total']):
            #    amount_dif = draft.amount_total - float(invoice['amount_total'])
            #    _logger.info("amount_dif: " + str(amount_dif))
            #if amount_dif != 0:
            #    if amount_dif > 0:
            #        draft.tax_line_ids[0].amount = draft.tax_line_ids[0].amount - amount_dif
            #    else:
            #        draft.tax_line_ids[0].amount = draft.tax_line_ids[0].amount + abs(amount_dif)
            #draft.tax_line_ids[0].amount = invoice['amount_tax']
            draft.journal_id = invoice['journal_id']

            # se adjunta xml
            #raise ValidationError(str(self.env['account.move'].search_read([('id','=',draft.id)],[])) + "\n\n" + str(bill['xml_file_data']) + "\n\n" + str(bill['filename']))
            self.attach_to_invoice(draft, bill['xml_file_data'], bill['filename'])
            
            draft.l10n_mx_edi_cfdi_name = bill['filename']
            #_logger.info("despues de attach_to_invoice..")
            if invoice_type == 'out_invoice' or invoice_type == 'out_refund':
                #draft.l10n_mx_edi_payment_method_id = self.payment_method_customer
                #draft.l10n_mx_edi_usage = self.usage_customer

                if self.invoice_status_customer == 'abierta':
                    # se valida factura
                    draft.payment_term_id = self.payment_term_customer_id
                    #draft.action_invoice_open()
                    
                    #draft._get_sequence_prefix()
                    #draft._set_sequence_next()
                    #_logger.info("sequence_number_next_prefix..: " + str(draft.sequence_number_next_prefix))
                    #_logger.info("sequence_number_next..: " + str(draft.sequence_number_next))
                    draft.action_invoice_open()
                    #_logger.info("despues de action_invoice_open..")
                    draft.l10n_mx_edi_pac_status = 'signed'
                    draft.l10n_mx_edi_sat_status = 'valid'
                ### Paga factura cliente
                if self.invoice_status_customer == 'pagada':
                    if draft.partner_id.property_payment_term_id:
                        draft.payment_term_id = draft.partner_id.property_payment_term_id
                    else:
                        if self.invoice_payment_type_customer == 'fecha_fin_mes':
                            year = datetime.now().year
                            month = datetime.now().month
                            day = calendar.monthrange(year, month)[1]
                            draft.date_invoice = datetime(year, month, day).date()
                        if self.invoice_payment_type_customer == 'fecha_especifica':
                            if not draft.date_invoice < self.invoice_date_customer:
                                draft.date_invoice = self.invoice_date_customer

                    #draft.action_invoice_open()
                    draft.action_invoice_open()
                    draft.l10n_mx_edi_pac_status = 'signed'
                    draft.l10n_mx_edi_sat_status = 'valid'
                    # si el termino de pago es contado, se valida la factura y se paga
                    # (solo para facturas de venta)

                    if self.is_immediate_term(draft.payment_term_id):
                        # Pago inmediato
                        #draft.payment_term_id = 13
                        # SE CREA PAGO DE FACTURA
                        payment = self.create_payment(draft, bill['bank_id'])
                        payment.post()
            else:
                ### Abierta factura proveedor
                if self.invoice_status_provider == 'abierta':
                    # se valida factura
                    draft.payment_term_id = self.payment_term_provider_id
                    #draft.action_invoice_open()
                    draft.action_invoice_open()
                    draft.l10n_mx_edi_pac_status = 'signed'
                    draft.l10n_mx_edi_sat_status = 'valid'
                ### Paga factura proveedor
                if self.invoice_status_provider == 'pagada':
                    if draft.partner_id.property_payment_term_id:
                        draft.payment_term_id = draft.partner_id.property_payment_term_id
                    else:
                        if self.invoice_payment_type_provider == 'fecha_fin_mes':
                            year = datetime.now().year
                            month = datetime.now().month
                            day = calendar.monthrange(year, month)[1]
                            draft.date_invoice = datetime(year, month, day).date()
                        if self.invoice_payment_type_provider == 'fecha_especifica':
                            if not draft.date_invoice < self.invoice_date_provider:
                                draft.date_invoice = self.invoice_date_provider

                    #draft.action_invoice_open()
                    draft.action_invoice_open()
                    draft.l10n_mx_edi_pac_status = 'signed'
                    draft.l10n_mx_edi_sat_status = 'valid'

                    if self.is_immediate_term(draft.payment_term_id):
                        # Pago inmediato
                        draft.payment_term_id = 13
                        payment = self.create_payment(draft, bill['bank_id'])
                        payment.post()
            partner_exists = self.get_partner_or_create_validation(draft.partner_id)

            if partner_exists:
                mensaje3 = 'Algunas facturas tienen un contacto con RFC que ya esxite en el sistema, vaya al menu "Contactos por combinar" para poder combinarlos.'

            invoice_ids.append(draft.id)

        mensaje1 = 'Facturas cargadas: ' + str(len(invoice_ids)) + '\n'
        mensaje1 = mensaje1 + mensaje3
        mensaje2 = mensaje1 + '\nFacturas no cargadas: ' + str(len(invalid_bills))
        invalids = '\n'.join(invalid_bills)
        mensaje2 = mensaje2 + '\n' + invalids
        view = self.env.ref('itl_descarga_masiva_facturas.sh_message_wizard')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = mensaje2
        context['invoice_ids'] = invoice_ids
        
        return invoice_ids, mensaje2
        """
        return {
            'name': 'Advertencia',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.message.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
        }
        """
    
    @api.onchange('invoice_status_customer')
    def _onchange_invoice_status_customer(self):
        if not self.invoice_status_customer:
            self.invoice_payment_type_customer = False
            self.invoice_date_provider = False

    @api.onchange('invoice_type', 'company_id')
    def _onchange_invoice_type(self):
        pass

    @api.onchange('uploaded_file')
    def onchnage_uploaded_file(self):
        if self.uploaded_file:
            file_ext = self.get_file_ext(self.filename)
            if file_ext.lower() not in ('xml', 'zip'):
                raise ValidationError('Por favor, escoja un archivo ZIP o XML')
            if file_ext.lower() == 'xml':
                raw_file = self.get_raw_file()
                bills = self.get_xml_data(raw_file)
                root = bills[0]['xml']['cfdi:Comprobante']
                vendor = root['cfdi:Receptor']
                vendor2 = root['cfdi:Emisor']
                rfc_receptor = vendor.get('@Rfc') or vendor.get('@rfc')
                rfc_emisor = vendor2.get('@Rfc') or vendor2.get('@rfc')
                self.validate_invoice_type(rfc_emisor, rfc_receptor)
                #raise UserError('okj')
            else:
                self.invoice_type = False
        else:
            self.invoice_type = False

    def validate_invoice_type(self, rfc_emisor, rfc_receptor):
        #raise ValidationError(rfc_emisor)
        #_logger.info("--> rfc_emisor: " + str(rfc_emisor))
        #_logger.info("--> rfc_receptor: " + str(rfc_receptor))
        emisor_company_id = self.env['res.company'].sudo().search([('vat', '=', rfc_emisor)])
        flag = True
        invoice_type = ''
        #_logger.info("if self.company_id == emisor_company_id: " + str(self.company_id) + " = " + str(emisor_company_id))
        if self.company_id == emisor_company_id:
            invoice_type = 'out_invoice'
            self.invoice_type = 'out_invoice'
            flag = False
            # return 'cliente'
        receptor_company_id = self.env['res.company'].sudo().search([('vat', '=', rfc_receptor)])
        #_logger.info("if self.company_id == receptor_company_id: " + str(self.company_id) + " = " + str(receptor_company_id))
        if self.company_id == receptor_company_id:
            invoice_type = 'in_invoice'
            self.invoice_type = 'in_invoice'
            flag = False
            # return 'proveedor'
        #_logger.info("if emisor_company_id == receptor_company_id: " + str(emisor_company_id) + " = " + str(receptor_company_id))
        if emisor_company_id == receptor_company_id:
            invoice_type = 'invalid_invoice'
            return invoice_type
        #_logger.info("flag: " + str(flag))
        if flag:
            invoice_type = 'invalid_invoice'
            return invoice_type
        else:
            return invoice_type

    def get_xml_data(self, file):
        '''
            Ordena datos de archivo xml
        '''
        xmls = []
        # convertir byte string a dict
        xml_string = file.decode('utf-8')
        xml_string = self.clean_xml(xml_string)
        xml = xmltodict.parse(xml_string)

        xml_file_data = base64.encodestring(file)

        bill = {
            'filename': self.filename,
            'xml': xml,
            'xml_file_data': xml_file_data,
        }
        xmls.append(bill)

        return xmls

    def get_xml_from_zip(self, zip_file):
        '''
            Extraer archivos del .zip.
            Convertir XMLs a diccionario para
            un manejo mas fácil de los datos.
        '''
        xmls = []
        for fileinfo in zip_file.infolist():
            file_ext = self.get_file_ext(fileinfo.filename)
            #_logger.info("name: " + str(fileinfo.filename))
            if file_ext in ('xml', 'XML'):
                # convertir byte string a dict
                xml_string = zip_file.read(fileinfo).decode('utf-8')
                xml_string = self.clean_xml(xml_string)
                xml = xmltodict.parse(xml_string)

                xml_file_data = base64.encodestring(zip_file.read(fileinfo))
                bill = {
                    'filename': fileinfo.filename,
                    'xml': xml,
                    'xml_file_data': xml_file_data,
                }
                xmls.append(bill)

        return xmls

    def clean_xml(self, xml_string):
        # Este método sirve para remover los caracteres que, en algunos XML, vienen al inicio del string antes del primer
        # caracter '<'
        new_ml_string = xml_string.split('<')
        to_remove = new_ml_string[0]
        new_ml_string = xml_string.replace(to_remove, '')
        # new_ml_string = new_ml_string.replace('&#xA;',' ')
        # new_ml_string = new_ml_string.replace('&quot;','"')

        return new_ml_string
    
    def get_file_ext(self,filename):
        """
        obtiene extencion de archivo, si este lo tiene
        fdevuelve false, si no cuenta con una aextension
        (no es archivo entonces)
        """
        file_ext = filename.split('.')
        if len(file_ext) > 1:
            file_ext = filename.split('.')[1]
            return file_ext
        return False
    
    def get_raw_file(self):
        '''Convertir archivo binario a byte string.'''
        return base64.b64decode(self.uploaded_file)

    def test(self):
        raise ValidationError('ccccc')
    
    def get_zip_file(self, raw_file):
        '''
            Convertir byte string a archivo zip
            Valida y tira errorsi el archivo subido 
            no era un zip.
        '''
        try:
            # how to parse bytes object into zip file
            # https://stackoverflow.com/q/32910099/            
            zf = zipfile.ZipFile(io.BytesIO(raw_file), 'r')
            return zf
        except zipfile.BadZipFile:
            return False
    
    def validate_bills(self):
        '''
            Función principal. Controla todo el flujo de
            importación al clickear el botón (parsea el archivo
            subido, lo valida, obtener datos de la factura y
            guardarla crea factura en estado de borrador).
        '''
        #raise ValidationError('oooooooooo')
        file_ext = self.get_file_ext(self.filename)
        if file_ext.lower() not in ('xml', 'zip'):
            raise ValidationError('Por favor, escoja un archivo ZIP o XML')

        raw_file = self.get_raw_file()
        zip_file = self.get_zip_file(raw_file)

        if zip_file:

            # extraer archivos dentro del .zip
            bills = self.get_xml_from_zip(zip_file)
        else:
            bills = self.get_xml_data(raw_file)

        valid_bills = []
        invalid_bills = []
        for bill in bills:
            mensaje = self.validations(bill)
            if mensaje:
                invalid_bills.append(mensaje)
                continue
            #raise ValidationError('ccccc')
            invoice, invoice_line, version, invoice_type, bank_id = self.prepare_invoice_data(bill)

            bill['bank_id'] = bank_id
            bill['invoice_type'] = invoice_type
            bill['invoice_data'] = invoice
            bill['invoice_line_data'] = invoice_line
            bill['version'] = version
            bill['valid'] = True

            mensaje = self.validations(bill)
            if mensaje:
                invalid_bills.append(mensaje)
                continue

            valid_bills.append(bill)

        # si todos son válidos, extraer datos del XML
        # y crear factura como borrador
        invoice_ids = []
        invoices_no_created = []
        warning_bills = []
        mensaje3 = ''
        for bill in valid_bills:
            invoice = bill['invoice_data']
            invoice_line = bill['invoice_line_data']
            invoice_type = bill['invoice_type']
            version = bill['version']
            
            if invoice_type == 'out_invoice' or invoice_type == 'out_refund':
                #_logger.info("invoice: " + str(invoice))
                draft, mensaje = self.create_bill_draft(invoice, invoice_line, invoice_type)
            else:
                draft, mensaje = self.create_bill_draft_vendor(invoice, invoice_line, invoice_type)

            draft.compute_taxes()
            #raise ValidationError(str(draft.state))
            # se asigna diario
            #_loger.info("draft_amount_tax: " +str(draft.amount_tax))
            #_loger.info("invoice['amount_tax']: " +str(invoice['amount_tax']))
            draft.tax_line_ids[0].amount = invoice['amount_tax']
            draft.journal_id = invoice['journal_id']
            #draft.account_id = invoice['account_id']

            # se adjunta xml
            #raise ValidationError(str(self.env['account.move'].search_read([('id','=',draft.id)],[])) + "\n\n" + str(bill['xml_file_data']) + "\n\n" + str(bill['filename']))
            self.attach_to_invoice(draft, bill['xml_file_data'], bill['filename'])
            
            draft.l10n_mx_edi_cfdi_name = bill['filename']

            if invoice_type == 'out_invoice' or invoice_type == 'out_refund':
                #draft.l10n_mx_edi_payment_method_id = self.payment_method_customer
                #draft.l10n_mx_edi_usage = self.usage_customer

                if self.invoice_status_customer == 'abierta':
                    # se valida factura
                    draft.payment_term_id = self.payment_term_customer_id
                    #draft.action_invoice_open()
                    draft.action_invoice_open()
                    draft.l10n_mx_edi_pac_status = 'signed'
                    draft.l10n_mx_edi_sat_status = 'valid'
                ### Paga factura cliente
                if self.invoice_status_customer == 'pagada':
                    if draft.partner_id.property_payment_term_id:
                        draft.payment_term_id = draft.partner_id.property_payment_term_id
                    else:
                        if self.invoice_payment_type_customer == 'fecha_fin_mes':
                            year = datetime.now().year
                            month = datetime.now().month
                            day = calendar.monthrange(year, month)[1]
                            draft.date_invoice = datetime(year, month, day).date()
                        if self.invoice_payment_type_customer == 'fecha_especifica':
                            if not draft.date_invoice < self.invoice_date_customer:
                                draft.date_invoice = self.invoice_date_customer

                    #draft.action_invoice_open()
                    draft.action_invoice_open()
                    draft.l10n_mx_edi_pac_status = 'signed'
                    draft.l10n_mx_edi_sat_status = 'valid'
                    # si el termino de pago es contado, se valida la factura y se paga
                    # (solo para facturas de venta)

                    if self.is_immediate_term(draft.payment_term_id):
                        # Pago inmediato
                        draft.payment_term_id = 13
                        # SE CREA PAGO DE FACTURA
                        payment = self.create_payment(draft, bill['bank_id'])
                        payment.post()
            else:
                ### Abierta factura proveedor
                if self.invoice_status_provider == 'abierta':
                    # se valida factura
                    draft.payment_term_id = self.payment_term_provider_id
                    #draft.action_invoice_open()
                    draft.action_invoice_open()
                    draft.l10n_mx_edi_pac_status = 'signed'
                    draft.l10n_mx_edi_sat_status = 'valid'
                ### Paga factura proveedor
                if self.invoice_status_provider == 'pagada':
                    if draft.partner_id.property_payment_term_id:
                        draft.payment_term_id = draft.partner_id.property_payment_term_id
                    else:
                        if self.invoice_payment_type_provider == 'fecha_fin_mes':
                            year = datetime.now().year
                            month = datetime.now().month
                            day = calendar.monthrange(year, month)[1]
                            draft.date_invoice = datetime(year, month, day).date()
                        if self.invoice_payment_type_provider == 'fecha_especifica':
                            if not draft.date_invoice < self.invoice_date_provider:
                                draft.date_invoice = self.invoice_date_provider

                    #draft.action_invoice_open()
                    draft.action_invoice_open()
                    draft.l10n_mx_edi_pac_status = 'signed'
                    draft.l10n_mx_edi_sat_status = 'valid'

                    if self.is_immediate_term(draft.payment_term_id):
                        # Pago inmediato
                        draft.payment_term_id = 13
                        payment = self.create_payment(draft, bill['bank_id'])
                        payment.post()
            partner_exists = self.get_partner_or_create_validation(draft.partner_id)

            if partner_exists:
                mensaje3 = 'Algunas facturas tienen un contacto con RFC que ya esxite en el sistema, vaya al menu "Contactos por combinar" para poder combinarlos.'

            invoice_ids.append(draft.id)

        mensaje1 = 'Facturas cargadas: ' + str(len(invoice_ids)) + '\n'
        mensaje1 = mensaje1 + mensaje3
        mensaje2 = mensaje1 + '\nFacturas no cargadas: ' + str(len(invalid_bills))
        invalids = '\n'.join(invalid_bills)
        mensaje2 = mensaje2 + '\n' + invalids
        view = self.env.ref('itl_descarga_masiva_facturas.sh_message_wizard')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = mensaje2
        context['invoice_ids'] = invoice_ids

        return {
            'name': 'Advertencia',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.message.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
        }

    def attach_to_invoice(self, invoice, xml, xml_name):
        """
        adjunta xml a factura
        """
        #_logger.info('attach_to_invoice: ',invoice)
        #_logger.info('invoice.l10n_mx_edi_cfdi_name: ',invoice.l10n_mx_edi_cfdi_name)
        #PREPARE VALUES
        sub_values = {
            'res_model': 'account.invoice',
            'res_id': invoice.id,
            #'name': invoice.l10n_mx_edi_cfdi_name,
            'name': xml_name,
            'datas': xml,
            'datas_fname': xml_name,
        }
        IrAttachment = self.env['ir.attachment'].sudo()
        attachment = IrAttachment.create(sub_values)
        return attachment
    
    def validations(self, bill):
        root = bill['xml']['cfdi:Comprobante']
        uuid = root['cfdi:Complemento']['tfd:TimbreFiscalDigital'].get('@UUID')
        ######## Tipo comprobante
        tipo_comprobante = root.get('@TipoDeComprobante') or root.get('@tipoDeComprobante')
        if tipo_comprobante.upper() in ['P', 'N']:
            mensaje = '{} - El XML contiene un Tipo de Comprobante {} que por el momento no puede ser procesado.'.format(
                bill['filename'], tipo_comprobante)
            return mensaje
        ######## Valida compañía
        vendor = root['cfdi:Receptor']
        vendor2 = root['cfdi:Emisor']
        rfc_receptor = vendor.get('@Rfc') or vendor.get('@rfc')
        rfc_emisor = vendor2.get('@Rfc') or vendor2.get('@rfc')
        # raise ValidationError(rfc_receptor + ' ' +bill['filename'])
        invoice_type = self.validate_invoice_type(rfc_emisor, rfc_receptor)

        if invoice_type == 'invalid_invoice':
            mensaje = '{} - La factura no corresponde a la compañía actual.'.format(bill['filename'])
            return mensaje
        ######## Valida Serie
        serie = root.get('@Serie') or root.get('@serie')
        #if invoice_type == 'out_invoice':
        #    if not serie:
        #        mensaje = '{} - El xml no contiene el atributo serie'.format(bill['filename'])
        #        return mensaje
        #    warehouse_id = False
        #    for line in self.company_id.xml_import_line_ids:
        #        if line.xml_import_journal_id.sequence_id.name == serie:
        #            warehouse_id = line.xml_import_warehouse_id.id
        #            break
        #    else:
        #        mensaje = '{} - No se encontro un diario configurado con la serie {} en la compañia seleccionada. Por favor configure uno.'.format(
        #            bill['filename'], serie)
        #        return mensaje
        ####### Valida almacén en facturas de provedor
        if invoice_type == 'in_invoice':
            warehouse_id = self.warehouse_provider_id and self.warehouse_provider_id.id or False
            if not warehouse_id:
                mensaje = '{} - Es una factura de proveedor y no se seleccionó un almacén.'.format(bill['filename'])
                return mensaje
        ####### Valida factura duplicada
        #amount_total = root.get('@Total') or root.get('@total')
        #date_invoice = root.get('@Fecha') or root.get('@fecha')
        folio = root.get('@Folio') or root.get('@folio') or False
        uuid = root['cfdi:Complemento']['tfd:TimbreFiscalDigital'].get('@UUID')
        #invoice_name = folio
        #invoice_exists = False
        #filename = bill['filename']
        ref = False

        if folio:
            ref = folio + ' - ' + uuid
        else:
            ref = uuid
        if invoice_type == 'out_invoice':
            invoice_exists = self.validate_duplicate_invoice(rfc_receptor, uuid, ref)
        else:
            invoice_exists = self.validate_duplicate_invoice(rfc_emisor, uuid, ref)
        if invoice_exists:
            mensaje = '{} - Esta factura ya existe en el sistema.'.format(uuid)
            return mensaje
        ####### Valida código SAT de producto
        if 'invoice_line_data' in bill:
            invoice_line = bill['invoice_line_data']
            for product in invoice_line:
                uom = False
                if self.import_type != 'start_amount':
                    uom = self.get_uom(product.get('sat_uom'))
                    if uom:
                        uom = uom[0].id
                    else:
                        uom = False

                        mensaje = '{} - La clave de undiad {} del XML no está asociada a ninguna unidad de medida del sistema.'.format(
                            bill['filename'], product.get('sat_uom'))
                        return mensaje
        ###### Valida productos
        #new_products = self.get_product_or_create_validation(root['cfdi:Conceptos']['cfdi:Concepto'], invoice_type)
        #if new_products and invoice_type == 'out_invoice':
        #    mensaje = '{} - Algunos productos en la factura de cliente no coinciden con el producto Pocari Sweat, favor de verificar.'.format(
        #        bill['filename'])
        #    return mensaje
        #elif new_products and invoice_type != 'out_invoice':
        #    mensaje = '{} - No se ha configurado el producto "Legacy invoice product" para las facturas de proveedor'.format(
        #        bill['filename'])
        #    return mensaje

        return False

    def get_partner_or_create_validation(self, partner):

        search_domain = [
            # '|', # obtener por nombre o RFC
            # ('name', '=', partner['name']),
            ('vat', '=', partner.vat),
            ('active', '=', True),
        ]

        if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            search_domain.append(('customer', '=', True))
        else:
            search_domain.append(('supplier', '=', True))

        p = self.env['res.partner'].search(search_domain)

        if len(p) > 1:
            return True

        return False

    def get_partner_or_create(self, partner):
        """
        sobrescritura de metodo, los nuevos partner se crearan con
        termino de pago 0 (contado), a menos que se especifique uno distinto
        """
        '''Obtener ID de un partner (proveedor). Si no existe, lo crea.'''
        search_domain = [
            # '|', # obtener por nombre o RFC
            ('name', '=', partner['name']),
            ('vat', '=', partner['rfc']),
            ('active', '=', True),
        ]

        #if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
        #    search_domain.append(('is_customer', '=', True))
        #else:
        #    search_domain.append(('supplier', '=', True))

        p = self.env['res.partner'].search(search_domain)

        # indica si se creara un partner generico
        create_generic = False

        if partner['rfc'] in ('XEXX010101000', 'XAXX010101000'):
            for partner_rec in p:
                if partner_rec.name == partner['name']:
                    p = [partner_rec, ]
                    break
            else:
                # si no encuentra un match de nombre, crear generico
                create_generic = True

        if not p or create_generic:
            # crear si el proveedor no existe
            payment_term_id = False
            if self.payment_term_id:
                payment_term_id = self.payment_term_id
            else:
                # se obtiene el termino de pago de inmediato
                payment_term_line_id = self.get_payment_term_line(0)
                if payment_term_line_id:
                    payment_term_id = payment_term_line_id.payment_id
            #raise ValidationError(str(partner.get('position_id')))
            #fiscal_position_code = partner.get('position_id')
            #fiscal_position = self.env['account.fiscal.position'].search(
            #    [('l10n_mx_edi_code', '=', fiscal_position_code)])
            #fiscal_position = fiscal_position and fiscal_position[0]
            #fiscal_position_id = fiscal_position.id or False

            vals = {
                'name': partner['name'],
                'vat': partner['rfc'],
                #'property_account_position_id': fiscal_position_id,
            }

            if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
                vals['property_payment_term_id'] = payment_term_id and payment_term_id.id or False
                vals['customer'] = True
                vals['supplier'] = False
            else:
                vals['property_supplier_payment_term_id'] = payment_term_id and payment_term_id.id or False
                vals['customer'] = False
                vals['supplier'] = True

            p = self.env['res.partner'].create(vals)
        else:
            p = p[0]

        return p

    def get_product_or_create_validation(self, products, invoice_type):
        """
        Valida que exista el producto 
        """
        # raise ValidationError('ok')
        if not isinstance(products, list):
            products = [products]

        products_ok = []
        products_new = []
        
        
        for product in products:
            invoice_line = {}

            extra_line = {}

            invoice_line['name'] = product.get('@Descripcion') or product.get('@descripcion')
            
            p = self.env['product.product'].search([
                ('name', '=', invoice_line['name'])
            ])
            p = p[0] if p else False
                
            if p:
                continue
            
            else:
                cantidad = float(product.get('@Cantidad') or product.get('@cantidad'))
                importe = float(product.get('@Importe') or product.get('@importe'))
                valor_unitario = str(importe / cantidad)
                invoice_line['price_unit'] = valor_unitario
                # datos para creacion de producto
                invoice_line['sat_product_ref'] = product.get('@ClaveProdServ') or product.get('@claveProdServ')
                invoice_line['product_ref'] = product.get('@NoIdentificacion') or product.get('@noIdentificacion')
                invoice_line['sat_uom'] = product.get('@ClaveUnidad') or product.get('@claveUnidad')
                
                EdiCode = self.env["l10n_mx_edi.product.sat.code"]

                product_vals = {
                    'name': invoice_line['name'],
                    'standard_price': invoice_line['price_unit'],
                    'default_code': invoice_line['product_ref'],
                    'type': 'product',
                }

                sat_code = EdiCode.search([("code","=",invoice_line['sat_product_ref'])])
                # #print("sat_code = ",sat_code)
                if sat_code:
                    product_vals["l10n_mx_edi_code_sat_id"] = sat_code[0].id

                uom = self.get_uom(invoice_line['sat_uom'])
                if uom:
                    product_vals["uom_id"] = uom[0].id
                    product_vals["uom_po_id"] = uom[0].id
                p = self.env['product.product'].create(product_vals)
                #raise ValidationError(str(product_vals))
                #temporal_product = self.env['legacy.invoice.product'].search([('name','=',product_vals['name'])])
                #raise ValidationError(str(temporal_product))
                #if len(temporal_product) > 0:
                #    continue
                #p = self.env['legacy.invoice.product'].create(product_vals)
        
        if len(products_new) > 0:
            return True
        else:
            return False

    def validate_duplicate_invoice(self, vat, uuid, ref):
        """
        REVISA SI YA EXISTE LA FACTURA EN SISTEMA
        DEVUELVE TRUE SI YA EXISTE
        FALSE SI NO
        """

        #date = date.split('T')[0]
        AccountInvoice = self.env['account.invoice'].sudo()

        #domain = [
        #    ('partner_id.vat', '=', vat),
        #    ('amount_total', '=', round(float(amount_total), 2)),
        #    ('invoice_date', '=', date),
        #    ('state', '!=', 'cancel'),
        #]
        #if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            # FACTURA CLIENTE
        domain = [('l10n_mx_edi_cfdi_name', '=', uuid),('company_id','=',self.company_id.id)]
        #_logger.info("filename: " + str(filename) + ' - ' + str(ref))
        #if ref:
            
        #    domain = [('state','!=','cancel'),('l10n_mx_edi_cfdi_name', '=', filename),('reference','=',ref),('company_id','=',self.company_id.id)]
            
        #else:
            # FACTURA PROVEEDOR
        #    domain.append(('ref', '=', invoice_name))
        #_logger.info("validate_duplicate_invoice domain: " + str(domain))
        invoices = AccountInvoice.search(domain)
        #_logger.info("Domain: " + str(domain))
        #_logger.info("Factura: " + str(invoices))
        if invoices:
            #print('DUPLICADA: ', invoices)
            return True
        return False

    def create_payment(self, invoice, bank_id):

        """
        Crea pago para la factura indicada
        """
        AccountRegisterPayments = self.env['account.register.payments'].sudo()
        if invoice.type == 'out_invoice':
            payment_type = 'inbound' if invoice.type in ('out_invoice', 'in_refund') else 'outbound'
            if payment_type == 'inbound':
                payment_method = self.env.ref('account.account_payment_method_manual_in')
            else:
                payment_method = self.env.ref('account.account_payment_method_manual_out')

            vals = {
                'company_id': self.company_id.id,
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': bank_id,
                'payment_type': payment_type,
                'payment_method_id': payment_method.id,
                'group_invoices': False,
                'invoice_ids': [(6, 0, [invoice.id])],
                'multi': False,
                'payment_date': invoice.date_invoice,
            }
        if invoice.type == 'in_invoice':
            vals = {
                'company_id': self.company_id.id,
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': bank_id,
                'payment_type': False,
                'payment_method_id': False,
                'group_invoices': False,
                'invoice_ids': [(6, 0, [invoice.id])],
                'multi': False,
                'payment_date': invoice.date_invoice,
            }
        account_register_payment_id = AccountRegisterPayments.with_context({'active_ids': [invoice.id, ]}).create(vals)
        payment_vals = account_register_payment_id.get_payments_vals()

        AccountPayment = self.env['account.payment'].sudo()
        return AccountPayment.create(payment_vals)

    def add_products_to_invoice(self, products, default_account, account_analytic_id, invoice_type):
        '''
            Obtener datos de los productos (Conceptos).
            SE SOBRESCRIBE PARA AGREGAR INFO DE CUENTA ANALITICA
        '''
        all_products = []

        # asegurarse de que `products` es una lista
        # para poder iterar sobre ella
        if not isinstance(products, list):
            products = [products]

        exent_tax = self.get_extra_line_tax()
        exent_tax = exent_tax and exent_tax.id or False
        #extra_line_account_id = self.get_extra_line_account()

        # crear un dict para cada producto en los conceptos
        for product in products:
            # datos básicos
            invoice_line = {}

            extra_line = {}  # se usara para productos gasolina, contendra lineas extra

            invoice_line['name'] = product.get('@Descripcion') or product.get('@descripcion')
            invoice_line['quantity'] = product.get('@Cantidad') or product.get('@cantidad')
            invoice_line['price_subtotal'] = product.get('@Importe') or product.get('@importe')
            # A. Marquez 28/12/19: Para obtener el valor unitario "correcto"
            cantidad = float(invoice_line['quantity'])
            importe = float(invoice_line['price_subtotal'])
            valor_unitario = str(importe / cantidad)
            ###
            # invoice_line['price_unit'] = product.get('@ValorUnitario') or product.get('@valorUnitario')
            invoice_line['price_unit'] = valor_unitario
            # datos para creacion de producto
            invoice_line['sat_product_ref'] = product.get('@ClaveProdServ') or product.get('@claveProdServ')
            invoice_line['product_ref'] = product.get('@NoIdentificacion') or product.get('@noIdentificacion')
            invoice_line['sat_uom'] = product.get('@ClaveUnidad') or product.get('@claveUnidad')

            analytic_tag_ids = False
            if invoice_type == 'out_invoice':
                if self.line_analytic_tag_customer_ids:
                    analytic_tag_ids = [(6, None, self.line_analytic_tag_customer_ids.ids)]
            else:
                if self.line_analytic_tag_provider_ids:
                    analytic_tag_ids = [(6, None, self.line_analytic_tag_provider_ids.ids)]

            invoice_line['analytic_tag_ids'] = analytic_tag_ids
            invoice_line['account_analytic_id'] = account_analytic_id
            if invoice_type == 'out_invoice':
                invoice_line['account_id'] = self.cuenta_ingreso_cliente_id.id
            else:
                invoice_line['account_id'] = self.cuenta_gasto_proveedor_id.id

            # calcular porcentaje del descuento, si es que hay
            if product.get('@Descuento'):
                invoice_line['discount'] = self.get_discount_percentage(product)
            else:
                invoice_line['discount'] = 0.0
            
            #raise ValidationError(str('invoice_line: ')+str(invoice_line))
            #if invoice_type == 'out_invoice':
                # obtener id del producto
                # crear producto si este no existe
            producto = self.get_product_or_create(invoice_line)
            invoice_line['product_id'] = producto.id
            #invoice_line['account_id'] = producto.categ_id.property_account_expense_categ_id.id
            #else:
            #    invoice_line['product_id'] = invoice_line
            # si el producto tiene impuestos, obtener datos
            # y asignarselos al concepto
            tax_group = ''
            check_taxes = product.get('cfdi:Impuestos')
            if check_taxes:
                invoice_taxes = []
                if check_taxes.get('cfdi:Traslados'):
                    traslado = {}
                    t = check_taxes['cfdi:Traslados']['cfdi:Traslado']
                    # print('---t----: ',t)
                    if not isinstance(t, list):
                        t = [t, ]
                    for element in t:
                        # revisa rsi es gasolina el producto
                        tax_base = element.get('@Base')
                        """
                        # si la base del impuesto no coincide con el subtotal del producto
                        # es que es gasolina
                        if tax_base != invoice_line['price_subtotal']:
                            #print("es gasolina")
                            new_price = float(tax_base) / float(invoice_line['quantity'])
                            invoice_line['price_unit'] = new_price

                            # calcular precio de linea extra
                            extra_line_price = float(invoice_line['price_subtotal']) - float(tax_base)

                            # revisar si no es necesario recalcular el subtotal
                            # invoice_line['price_unit'] = new_price * invoice_line['quantity']

                            extra_account_id = extra_line_account_id and extra_line_account_id.id or False
                            if not extra_account_id:
                                raise ValidationError('No se encontro una cuenta de combustible configurada')

                            # crear linea extra
                            extra_line = {
                                'name': invoice_line['name'],
                                'quantity': 1,
                                # 'product_id': invoice_line['product_id'],
                                'price_unit': extra_line_price,
                                'price_subtotal': extra_line_price,
                                'sat_product_ref': invoice_line['sat_product_ref'],
                                'product_ref': invoice_line['product_ref'],
                                'sat_uom': invoice_line['sat_uom'],
                                'ignore_line': True,
                                'account_id': extra_line_account_id and extra_line_account_id.id or False,
                                'account_analytic_id': account_analytic_id,
                                'analytic_tag_ids': False,
                            }

                            if exent_tax:
                                extra_line['taxes'] = [(6, None, (exent_tax,))]
                        """
                        tax_code = element.get('@Impuesto', '')
                        tax_rate = element.get('@TasaOCuota', '0')
                        tax_factor = element.get('@TipoFactor', '')
                        tax_group = tax_group + tax_code + '|' + tax_rate + '|tras|' + tax_factor + ','
                        # tax = self.get_tax_ids(tax_group)
                        # traslado['tax_id'] = tax
                        # invoice_taxes.append(tax)

                if check_taxes.get('cfdi:Retenciones'):
                    retencion = {}
                    r = check_taxes['cfdi:Retenciones']['cfdi:Retencion']
                    if not isinstance(r, list):
                        r = [r, ]
                    for element in r:
                        # retencion['amount'] = element.get('@Importe') or element.get('@importe')
                        # retencion['base'] = element.get('@Base')
                        # retencion['account_id'] = 23
                        tax_code = element.get('@Impuesto', '')
                        tax_rate = element.get('@TasaOCuota', '0')
                        tax_factor = element.get('@TipoFactor', '')
                        tax_group = tax_group + tax_code + '|' + tax_rate + '|ret|' + tax_factor + ','
                        # tax = self.get_tax_ids(tax_group)
                        # retencion['tax_id'] = tax
                        # invoice_taxes.append(tax)
                taxes = False
                
                if tax_group:
                    taxes = self.get_tax_ids(tax_group)
                    #raise ValidationError(str(taxes))
                invoice_line['taxes'] = taxes

            # agregar concepto a la lista de conceptos
            all_products.append(invoice_line)

            # se agrega linea extra, de existir
            if extra_line:
                all_products.append(extra_line)

        return all_products
    
    def get_payment_term_line(self, days):
        '''
        obtiene linea de termino de pago indicado,
        se podra accedfer al termino de pago desde el campo payment_id
        days: in que representa el no. de dias del t. de pago a buscar
        '''
        payment_term_line_id = False
        PaymentTermLine = self.env['account.payment.term.line']
        domain = [('days','=',days),('payment_id.company_id','=',self.company_id.id)]
        #print('domain: ',domain)
        payment_term_line_id = PaymentTermLine.search(domain)
        if payment_term_line_id:
            #print('payment_term_line_id')
            payment_term_line_id = payment_term_line_id[0]
        return payment_term_line_id
    
    def get_discount_percentage(self, product):
        '''Calcular descuento de un producto en porcentaje.'''
        
        d = (float(product['@Descuento']) / float(product['@Importe'])) * 100
        return d
    
    def get_extra_line_account(self):
        """
        busca cuenta para la liena extra
        """
        AccountAccount = self.env['account.account']
        res = AccountAccount.search([('gas_default','=',True),('company_id','=',self.company_id.id)])
        return res and res[0] or False
    
    def get_uom(self, sat_code):
        """
        obtiene record de unidad de medida o lo crea
        sat_code: string con el codigo del sat de la unidad de medida
        """
        ProductUom = self.env["uom.uom"]
        result = ProductUom.search([("l10n_mx_edi_code_sat_id.code", "=", sat_code)])
        if not result:
            sat_code_result = self.env['l10n_mx_edi.product.sat.code'].search([('code','=',sat_code)])
            if sat_code_result:
                category_uom_id = self.env['uom.category'].search([('measure_type','=','unit')])[0]
                result = ProductUom.create({'name': sat_code,
                                        'l10n_mx_edi_code_sat_id': sat_code_result.id,
                                        'category_id': category_uom_id.id,
                                        'uom_type': 'smaller'})
            else:
                result = False
        return result
    
    def get_product_or_create(self, product):
        '''Obtener ID de un producto. Si no existe, lo crea.'''
        #_logger.info('get_product_or_create')
        p = self.env['product.product'].search([
            ('name', '=', product['name'])
        ])
        p = p[0] if p else False
        #_logger.info('p: ',p)
        if not p:
            # crear producto si no existe
            EdiCode = self.env["l10n_mx_edi.product.sat.code"]

            product_vals = {
                'name': product['name'],
                'price': product['price_unit'],
                'default_code': product['product_ref'],
                'type': 'product',
            }

            sat_code = EdiCode.search([("code","=",product['sat_product_ref'])])
            #_logger.info("sat_code = ",sat_code)
            if sat_code:
                product_vals["l10n_mx_edi_code_sat_id"] = sat_code[0].id

            uom = self.get_uom(product['sat_uom'])
            #_logger.info(product['sat_uom'])
            #_logger.info("uom = ",uom)
            if uom:
                product_vals["uom_id"] = uom[0].id
                product_vals["uom_po_id"] = uom[0].id

            p = self.env['product.product'].create(product_vals)
        # if not p:
        #     raise UserError("No se encontro el un producto con nombre '{}'".format(product['name']))
        if not p:
            return False
        return p
        
    """
    def get_legacy_invoice_product(self, product):
        
        legacy_invoice_product = self.env['product.product'].search(['|',
                                                                    ('name', 'ilike','Legacy Invoice Product'),
                                                                    ('default_code','=','legacy_invoice_product')])
        
        if self.create_product:
            
            EdiCode = self.env["l10n_mx_edi.product.sat.code"]

            product_vals = {
                'name': product['name'],
                'price': product['price_unit'],
                'default_code': product['product_ref'],
                'type': 'product',
            }

            sat_code = EdiCode.search([("code","=",product['sat_product_ref'])])
            # #print("sat_code = ",sat_code)
            if sat_code:
                product_vals["l10n_mx_edi_code_sat_id"] = sat_code[0].id

            uom = self.get_uom(product['sat_uom'])
            # #print(product['sat_uom'])
            # #print("uom = ",uom)
            if uom:
                product_vals["uom_id"] = uom[0].id
                product_vals["uom_po_id"] = uom[0].id

            p = self.env['product.product'].create(product_vals)

        return p.id
    """

    def create_bill_draft(self, invoice, invoice_line, invoice_type):
        '''
            Toma la factura y sus conceptos y los guarda
            en Odoo como borrador.
        '''
        #_logger.info("invoice: " + str(invoice))
        #raise ValidationError(str(invoice))
        vals = {
            # 'name': name,
            'company_id': self.company_id.id,
            'l10n_mx_edi_cfdi_name': invoice['l10n_mx_edi_cfdi_name'],
            'l10n_mx_edi_cfdi_name2': invoice['l10n_mx_edi_cfdi_name'],
            'l10n_mx_edi_cfdi_uuid': invoice['uuid'],
            'journal_id': invoice['journal_id'],
            'team_id': invoice['team_id'],
            'user_id': invoice['user_id'],
            'date_invoice': invoice['date_invoice'],
            'l10n_mx_edi_payment_method_id': invoice['l10n_mx_edi_payment_method_id'],
            'l10n_mx_edi_usage': invoice['l10n_mx_edi_usage'],
            'account_id': invoice['account_id'],
            'partner_id': invoice['partner_id'],
            'amount_untaxed': invoice['amount_untaxed'],
            'amount_tax': invoice['amount_tax'],
            'amount_total': invoice['amount_total'],
            'currency_id': invoice['currency_id'],
            'type': invoice['type'],
            #'warehouse_id': invoice['warehouse_id'],
            'is_start_amount': True if self.import_type == 'start_amount' else False,
            'operating_unit_id': False
        }
        
        #if invoice_type == 'out_invoice' or invoice_type == 'out_refund':
            #vals['name'] = invoice['name']
        
        vals['reference'] = invoice['ref']
        #else:
        vals['name'] = invoice['folio']
            #vals['create_return'] = False

        # How to create and validate Vendor Bills in code?
        # https://www.odoo.com/forum/ayuda-1/question/131324
        draft = self.env['account.invoice'].create(vals)
        #_logger.info("draft: " + str(draft))
        #raise ValidationError(str(self.env['account.move'].search_read([('id','=',draft.id)], [])))
        lines = []
        # asignar productos e impuestos a factura
        #_logger.info("draft: " + str(draft))
        #_logger.info("invoice_line: " + str(invoice_line))
        for product in invoice_line:
            uom = False
            if self.import_type != 'start_amount':
                uom = self.get_uom(product.get('sat_uom'))
                if uom:
                    uom = uom[0].id
                else:
                    uom = False

                    mensaje = '{} - La unidad de medida ' + str(
                        product.get('sat_uom')) + ' del XML no existe en el sistema.'
                    return False, mensaje
            self.env['account.invoice.line'].create({
                'product_id': product.get('product_id'),
                'name': product.get('name'),
                'invoice_id': draft.id,
                #'name_legacy': product['name'],
                'quantity': float(product['quantity']),
                'price_unit': float(product['price_unit']),
                'account_id': product['account_id'],
                'discount': float(product.get('discount')) or 0.0,
                'price_subtotal': float(product['price_subtotal']),
                'invoice_line_tax_ids': product.get('taxes'),
                'uom_id': uom,
                'analytic_tag_ids': product['analytic_tag_ids'],
                'account_analytic_id': product['account_analytic_id'],
                'company_id': self.company_id.id
            })
            #self.env['account.move.line'].create()
        #_logger.info("salió de crear lineas")
        #draft.invoice_line_ids = lines
        #draft._compute_amount()
        return draft, False
    
    def create_bill_draft_vendor(self, invoice, invoice_line, invoice_type):
        '''
            Toma la factura y sus conceptos y los guarda
            en Odoo como borrador.
        '''
        #raise ValidationError(str('payment way: ')+str(invoice))
        vals = {
            # 'name': name,
            #'l10n_mx_edi_cfdi_name': invoice['l10n_mx_edi_cfdi_name'],
            #'l10n_mx_edi_cfdi_name2': invoice['l10n_mx_edi_cfdi_name'],
            'company_id': self.company_id.id,
            'journal_id': invoice['journal_id'],
            'team_id': invoice['team_id'],
            'user_id': invoice['user_id'],
            'date_invoice': invoice['date_invoice'],
            'l10n_mx_edi_payment_method_id': invoice['l10n_mx_edi_payment_method_id'],
            'l10n_mx_edi_usage': invoice['l10n_mx_edi_usage'],
            'account_id': invoice['account_id'],
            'date': invoice['date_invoice'],
            'partner_id': invoice['partner_id'],
            'amount_untaxed': invoice['amount_untaxed'],
            'amount_tax': invoice['amount_tax'],
            'amount_total': invoice['amount_total'],
            'currency_id': invoice['currency_id'],
            'type': invoice['type'],
            #'warehouse_id': invoice['warehouse_id'],
            'is_start_amount': True if self.import_type == 'start_amount' else False,
            'operating_unit_id': False
        }

        #if invoice_type == 'out_invoice' or invoice_type == 'out_refund':
        #_logger.info("ref: " + str(invoice['ref']))
        vals['reference'] = invoice['ref']
        #else:
        #    vals['ref'] = invoice['name']
            #vals['create_return'] = False

        # How to create and validate Vendor Bills in code?
        # https://www.odoo.com/forum/ayuda-1/question/131324
        draft = self.env['account.invoice'].create(vals)
        
        lines = []
        
        partner_invoice_id = self.env['res.partner'].browse(invoice['partner_id'])

        # asigna el producto Legacy invoice a factura de proveedor
        # se crean productos en una tabla alterna para productos provinientes de facturas de proveedor
            
        for product in invoice_line:
            uom = False
            if self.import_type != 'start_amount':
                uom = self.get_uom(product.get('sat_uom'))
                if uom:
                    uom = uom[0].id
                else:
                    uom = False

                    mensaje = '{} - La unidad de medida ' + str(
                        product.get('sat_uom')) + ' del XML no existe en el sistema.'
                    return False, mensaje
            
            legacy_invoice_product = self.env['product.product'].search(['|',('name', 'ilike','Legacy Invoice Product'),('default_code','=','legacy_invoice_product')])
            
            product_words = self.env['product.words'].search([])
            product_name = product['name']
            product_name_org = product_name
            product_name = product_name.lower()
            related_product = False
            #_logger.info("product_line: " + str(product_name_org))
            for pw in product_words:
                if pw.keywords:
                    if '|' in pw.keywords:
                        words_list = pw.keywords.split('|')
                    else:
                        words_list = [pw.keywords]
                    words_list = [w.lower() for w in words_list]
                    _logger.info("product_name: " + str(product_name))
                    _logger.info("words_list: " + str(words_list))
                    if any(w in product_name for w in words_list):
                        if pw.partner_id:
                            _logger.info("parter_comparssion: " + str(partner_invoice_id) + " = " + str(pw.partner_id))
                            _logger.info("parter_comparssion 2: " + str(partner_invoice_id.name) + " = " + str(pw.partner_id.name))
                            if partner_invoice_id.vat == pw.partner_id.vat:
                                related_product = pw.product_id
                            else:
                                continue
                        else:
                            related_product = pw.product_id
                        _logger.info("related_product: " + str(related_product))
                        break
            #_logger.info("final related_product: " + str(related_product))
            product_id = False
            if not related_product:
                if not legacy_invoice_product:
                    pd_id = self.env['product.product'].browse(product.get('product_id'))
                    related_product = pd_id
                else:
                    related_product = legacy_invoice_product.id
            #_logger.info("account_id line: " + str(product['account_id']))
            self.env['account.invoice.line'].create({
                    'product_id': related_product.id,
                    'invoice_id': draft.id,
                   # 'name_legacy': product_name_org,
                    'name': related_product.name,
                    'quantity': float(product['quantity']),
                    'price_unit': float(product['price_unit']),
                    'account_id': product['account_id'],
                    'discount': float(product.get('discount')) or 0.0,
                    'price_subtotal': float(product['price_subtotal']),
                    'invoice_line_tax_ids': product.get('taxes'),
                    'uom_id': uom,
                    'analytic_tag_ids': product['analytic_tag_ids'],
                    'account_analytic_id': product['account_analytic_id'],
                    'company_id': self.company_id.id
                })
        #raise ValidationError(str("debug"))
        #draft.invoice_line_ids = lines
        #draft._compute_amount()
        return draft, False

    def prepare_invoice_data(self, bill):
        '''
            Obtener datos del XML y wizard para llenar factura
            Returns:
                invoice: datos generales de la factura.
                invoice_line: conceptos de la factura.
        '''
        #raise ValidationError('ooook')
        # aquí se guardaran los datos para su posterior uso
        invoice = {}
        invoice_line = []
        partner = {}

        filename = bill['filename']

        # elementos principales del XML
        root = bill['xml']['cfdi:Comprobante']

        # revisa version
        version = root.get('@Version') or root.get('@version') or ''
        vendor = root['cfdi:Receptor']
        vendor2 = root['cfdi:Emisor']
        rfc_receptor = vendor.get('@Rfc') or vendor.get('@rfc')
        rfc_emisor = vendor2.get('@Rfc') or vendor2.get('@rfc')

        invoice_type = self.validate_invoice_type(rfc_emisor, rfc_receptor)

        if invoice_type == 'out_invoice' or invoice_type == 'out_refund':
            # xml de cliente
            vendor = root['cfdi:Receptor']
            vendor2 = root['cfdi:Emisor']
        else:
            # xml de proveedor
            vendor = root['cfdi:Emisor']
            vendor2 = root['cfdi:Receptor']

        # obtener datos del partner
        partner['rfc'] = vendor.get('@Rfc') or vendor.get('@rfc')
        invoice['rfc'] = vendor.get('@Rfc') or vendor.get('@rfc')
        invoice['company_rfc'] = vendor2.get('@Rfc') or vendor2.get('@rfc')
        partner['name'] = vendor.get('@Nombre', False) or vendor.get('@nombre', 'PARTNER GENERICO: REVISAR')
        partner['position_id'] = vendor.get('@RegimenFiscal')
        partner_rec = self.get_partner_or_create(partner)
        default_account = partner_rec.default_xml_import_account and \
                          partner_rec.default_xml_import_account.id or False
        partner_id = partner_rec.id

        serie = root.get('@Serie') or root.get('@serie') or False
        folio = root.get('@Folio') or root.get('@folio') or False
        invoice['folio'] = folio
        no_certificado = root.get('@NoCertificado') or root.get('@nocertificado') or False
        metodopago = root.get('@MetodoPago') or root.get('@metodoPago') or False
        forma_pago = root.get('@FormaPago') or root.get('@formaPago')
        uso_cfdi = root['cfdi:Receptor'].get('@UsoCFDI') or root['cfdi:Receptor'].get('@usoCFDI')

        journal_id, analytic_account_id, warehouse_id, bank_id = self.get_company_xml_import_data(invoice_type, serie)
        
        invoice['journal_id'] = journal_id
        invoice['warehouse_id'] = warehouse_id
        invoice['metodo_pago'] = metodopago

        forma_pago_rec = self.get_edi_payment_method(forma_pago)
        #raise ValidationError(str(forma_pago_rec.name) + " - " + str(uso_cfdi))
        invoice['l10n_mx_edi_payment_method_id'] = forma_pago_rec and forma_pago_rec.id or False
        invoice['l10n_mx_edi_usage'] = uso_cfdi

        # obtener datos de los conceptos.
        # invoice_line es una lista de diccionarios
        # invoice_line = self.add_products_to_invoice(root['cfdi:Conceptos']['cfdi:Concepto'])
        if self.import_type == 'start_amount':
            # carga de saldfos iniciales, las lineas se agrupan por impuesto
            if version == '3.3':
                invoice_line = self.compact_lines(root['cfdi:Conceptos']['cfdi:Concepto'], default_account)
            else:
                taxes = self.get_cfdi32_taxes(root['cfdi:Impuestos'])
                invoice_line = self.get_cfdi32(root['cfdi:Conceptos']['cfdi:Concepto'], taxes, default_account,
                                               analytic_account_id)
        else:
            # carga de factura regular
            invoice_line = self.add_products_to_invoice(root['cfdi:Conceptos']['cfdi:Concepto'], default_account,
                                                        analytic_account_id, invoice_type)
            
        # raise ValidationError(str('after add_products_to_invoice'))
        # obtener datos de proveedor
        # crear al proveedor si no existe
        tipo_comprobante = root.get('@TipoDeComprobante') or root.get('@tipoDeComprobante')
        invoice['tipo_comprobante'] = tipo_comprobante
        # SE CORRIGE TIPO SEGUN EL TIPO DE COMPROBANTE
        # SOLO TOMA EN CUENTA INGRESOS Y EGRESOS
        corrected_invoice_type = False
        if tipo_comprobante.upper() == 'E':
            if invoice_type == 'out_invoice':
                corrected_invoice_type = 'out_refund'
            else:
                corrected_invoice_type = 'in_refund'

        # partner['rfc'] = vendor.get('@Rfc') or vendor.get('@rfc')
        # invoice['rfc'] = vendor.get('@Rfc') or vendor.get('@rfc')
        # invoice['company_rfc'] = vendor2.get('@Rfc') or vendor2.get('@rfc')
        # partner['name'] = vendor.get('@Nombre',False) or vendor.get('@nombre','PARTNER GENERICO: REVISAR')

        # partner['position_id'] = vendor.get('@RegimenFiscal')
        moneda = root.get('@Moneda') or root.get('@moneda') or 'MXN'
        # print('moneda.upper(): ',moneda.upper())
        if moneda.upper() in ('M.N.', 'XXX', 'PESO MEXICANO'):
            moneda = 'MXN'

        # obtener datos generales de la factura
        #_logger.info('moneda: ' + str(moneda))
        currency = self.env['res.currency'].search([('name', '=', moneda)])
        
        # print('self.invoice_type: ',self.invoice_type)
        # invoice['type'] = 'in_invoice' # factura de proveedor

        invoice['type'] = corrected_invoice_type or invoice_type
        
        if folio:
            invoice['ref'] = folio + ' - ' + filename
            
        else:
            invoice['ref'] = filename
        #if not folio:
        #    invoice['name'] = no_certificado
        #_logger.info('create_filename: ' + str(filename))
        #_logger.info('create_ref: ' + str(invoice['ref']))
        
        invoice['amount_untaxed'] = root.get('@SubTotal') or root.get('@subTotal')
        #invoice['amount_tax'] = root['cfdi:Impuestos']['cfdi:Traslados']['cfdi:Traslado'].get('@Importe')

        invoice['amount_tax'] = False
        if 'cfdi:Impuestos' in  root and root['cfdi:Impuestos'] != None:
            invoice['amount_tax'] = root['cfdi:Impuestos'].get('@TotalImpuestosTrasladados')
        invoice['amount_total'] = root.get('@Total') or root.get('@total')
        invoice['partner_id'] = partner_id
        invoice['currency_id'] = currency.id
        invoice['date_invoice'] = root.get('@Fecha') or root.get('@fecha')
        # invoice['account_id'] = self.env['account.invoice']._default_journal().id

        ####
        invoice['l10n_mx_edi_cfdi_name'] = filename
        # invoice['l10n_mx_edi_cfdi_name2'] = filename #DENOTA QUE SE CARGO POR MEDIO DE ESTE MODULO
        # invoice['journal_id'] = self.journal_id and self.journal_id.id or False
        invoice['team_id'] = self.team_id and self.team_id.id or False
        invoice['user_id'] = self.user_id and self.user_id.id or False
        
        # account_id fue quitado para la v13 de odoo
        if invoice_type == 'out_invoice':
            #raise ValidationError('ooook')
            invoice['account_id'] = self.cuenta_cobrar_cliente_id.id
        else:
            #raise ValidationError('ooook')
            invoice['account_id'] = self.cuenta_pagar_proveedor_id.id
        # OBTENER UUID
        uuid = root['cfdi:Complemento']['tfd:TimbreFiscalDigital'].get('@UUID')
        invoice['uuid'] = uuid
        return invoice, invoice_line, version, invoice_type, bank_id
    
    def get_tax_ids(self, tax_group, version='3.3'):
        #print('get_tax_ids: ',tax_group)
        '''
        obtiene los ids de los impuestos
        a partir de nombres de grupos de impuestos
        estructura:
        000|0.16,001|0.0,
        regresa [(6, None, ids)]
        '''
        tax_ids = []
        AccountTax = self.env['account.tax'].sudo()
        
        if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            type_tax_use = 'sale'
        else:
            type_tax_use = 'purchase'

        #se elimina ultima ,
        tax_group = tax_group[:-1]
        taxes = tax_group.split(',')
        #raise ValidationError(str(taxes))
        for tax in taxes:
            #print('tax: ', tax)
            if tax:
                tax_data = tax.split('|')
                tax_number = tax_data[0]
                tax_type = tax_data[2]

                
                domain = [
                    #('tax_code_mx','=',tax_number),
                    #('amount','=',rate),
                    ('type_tax_use','=',type_tax_use),
                    ('company_id','=',self.company_id.id),
                    #('l10n_mx_cfdi_tax_type','=',tax_factor),
                    ]
                tax_factor = False
                if len(tax_data) == 4: #si es 3.3 tendra 4 elementos
                    tax_factor = tax_data[3]
                    domain.append(('l10n_mx_cfdi_tax_type','=',tax_factor))

                if version == '3.3':
                    #3.3
                    if tax_factor != 'Exento':
                        tax_rate = float(tax_data[1])
                        if tax_type == 'tras':
                            rate = (tax_rate*100)
                        else:
                            rate = -(tax_rate*100)
                        domain.append(('amount','=',rate))

                    domain.append(('tax_code_mx','=',tax_number))
                else:
                    #   3.2
                    if tax_data[1] != 'xxx':
                        tax_rate = float(tax_data[1])
                        if tax_type == 'tras':
                            rate = tax_rate
                        else:
                            rate = -(tax_rate)
                        domain.append(('amount','=',rate))
                    domain.append(('name','ilike',tax_number))
                #print('DOMAIN: ',domain)
                tax_id = AccountTax.search(domain)
                #raise ValidationError(str(domain))
                if tax_id:
                    tax_id = tax_id[0].id
                    tax_ids.append(tax_id)
        if tax_ids:
            #print('tax_ids: ',tax_ids)
            return [(6, None, tax_ids)]
        return False
    
    def get_edi_payment_method(self, code):
        """
        busca metodo de pago a partir de codigo 
        y lo devuelve
        """
        #print('get_edi_payment_method: ',code)
        PaymentMethod = self.env['l10n_mx_edi.payment.method']
        res = PaymentMethod.search([('code','=',code)])
        return res and res[0] or False
    
    def get_extra_line_tax(self):
        """
        busca impuesto de tipo exento y lo devuelve
        """
        AccountTax = self.env['account.tax']
        type_tax_use = 'sale' if self.invoice_type == 'out_invoice' else 'purchase'
        res = AccountTax.search([('l10n_mx_cfdi_tax_type','=','Exento'),
                                ('type_tax_use','=',type_tax_use),
                                ('company_id','=',self.company_id.id),])
        return res and res[0] or False
    
    def get_cfdi32(self, products, taxes, default_account, analytic_account_id):
        """
        SE SOBRESCRIBE PARA AGREGAR INFO DE CUENTA ANALITICA
        """
        if not isinstance(products, list):
            products = [products]
        #print('products: ',products)
        all_products = []
        amount = 0
        for product in products:
            amount += (float(product.get('@importe',0)) - float(product.get('@descuento',0)))

        #print('amount: ',amount)


        taxes = self.get_tax_ids(taxes,'3.2')
        invoice_line = {}
        invoice_line['name'] = 'SALDOS INICIALES'
        invoice_line['quantity'] = 1

        analytic_tag_ids = False
        if self.line_analytic_tag_ids:
            analytic_tag_ids = [(6, None, self.line_analytic_tag_ids.ids)]

        invoice_line['analytic_tag_ids'] = analytic_tag_ids
        invoice_line['account_analytic_id'] = analytic_account_id
        invoice_line['account_id'] = default_account or self.line_account_id.id
        invoice_line['price_subtotal'] = amount
        invoice_line['price_unit'] = amount
        invoice_line['taxes'] = taxes
        all_products.append(invoice_line)
        return [invoice_line]
    
    def get_cfdi32_taxes(self,taxes):
        tax_group = ''
        if taxes:
            if float(taxes.get('@totalImpuestosTrasladados',0)) > 0:
                if type(taxes.get('cfdi:Traslados').get('cfdi:Traslado')) == list:
                    for item in taxes.get('cfdi:Traslados').get('cfdi:Traslado'):
                        tax_code = item.get('@impuesto')
                        tax_rate = item.get('@tasa')
                        if tax_code and tax_rate:
                            tax_group = tax_group + tax_code + '|' + tax_rate + '|tras,'
                else:
                    tax_code = taxes['cfdi:Traslados'].get('cfdi:Traslado').get('@impuesto')
                    tax_rate = taxes['cfdi:Traslados'].get('cfdi:Traslado').get('@tasa')
                    if tax_code and tax_rate:
                        tax_group = tax_group + tax_code + '|' + tax_rate + '|tras,'
        return tax_group

    
    def compact_lines(self, products, default_account):
        '''
          Rebisa las lienas de factura en el xml.
          y crea una sola linea por impuesto
        '''
        all_products = []
        #print('------->products: ',products)
        # asegurarse de que `products` es una lista
        # para poder iterar sobre ella
        if not isinstance(products, list):
            products = [products]
        # se guardan grupos de impuestos
        tax_groups = {}

        # crear un dict para cada producto en los conceptos
        for product in products:
            tax_group = ''
            # si el producto tiene impuestos, obtener datos
            # y asignarselos al concepto
            check_taxes = product.get('cfdi:Impuestos')
            if check_taxes:
                taxes = check_taxes.get('cfdi:Traslados')
                if taxes:
                    #print('type(taxes): ',type(taxes.get('cfdi:Traslado')))
                    if type(taxes.get('cfdi:Traslado')) == list:
                        #print('LISTAA: ',taxes)
                        for item in taxes.get('cfdi:Traslado'):
                            #print('item: ',item)
                            tax_code = item.get('@Impuesto','')
                            tax_rate = item.get('@TasaOCuota','0')
                            tax_factor = item.get('@TipoFactor','')
                            if tax_code:
                                tax_group = tax_group + tax_code + '|' + tax_rate + '|tras|' + tax_factor + ','
                    else:
                        tax_code = taxes.get('cfdi:Traslado').get('@Impuesto','')
                        tax_rate = taxes.get('cfdi:Traslado').get('@TasaOCuota','0')
                        tax_factor = taxes.get('cfdi:Traslado').get('@TipoFactor','')
                        if tax_code:
                            tax_group = tax_group + tax_code + '|' + tax_rate + '|tras|' + tax_factor + ','


                taxes = check_taxes.get('cfdi:Retenciones')
                if taxes:
                    #print('taxes.get(cfdi:Retencion)',taxes.get('cfdi:Retencion'))
                    if type(taxes.get('cfdi:Retencion')) == list:
                        for item in taxes.get('cfdi:Retencion'):
                            #print('item: ',item)
                            tax_code = item.get('@Impuesto','')
                            tax_rate = item.get('@TasaOCuota','0')
                            tax_factor = item.get('@TipoFactor','')
                            if tax_code:
                                tax_group = tax_group + tax_code + '|' + tax_rate + '|ret|' + tax_factor + ','
                    else:
                        tax_code = taxes.get('cfdi:Retencion').get('@Impuesto')
                        tax_rate = taxes.get('cfdi:Retencion').get('@TasaOCuota')
                        tax_factor = taxes.get('cfdi:Retencion').get('@TipoFactor')
                        if tax_code:
                            tax_group = tax_group + tax_code + '|' + tax_rate + '|ret|' + tax_factor + ','

            # se agrega improte acumulado del producto por grupo de impuestos
            #print('--------->tax_groups: ',tax_groups)
            if tax_group in tax_groups:
                #print(float(product.get('@Descuento',0.0)))
                tax_groups[tax_group]['price_subtotal'] += ((float(product['@Importe'])) - float(product.get('@Descuento',0.0)))
            else:
                #print(float(product.get('@Descuento',0.0)))
                tax_groups[tax_group] = {}
                tax_groups[tax_group]['price_subtotal'] = ((float(product['@Importe'])) - float(product.get('@Descuento',0.0)))

            # agregar concepto a la lista de conceptos
            #all_products.append(invoice_line)

        # se crean las lineas por cada grupo de impuestos
        for group in tax_groups:
            _logger.info("tax_groups: " + str(group))
            #print('group: ',group)
            taxes = self.get_tax_ids(group)
            invoice_line = {}
            invoice_line['name'] = 'SALDOS INICIALES'
            invoice_line['quantity'] = 1

            analytic_tag_ids = False
            if self.line_analytic_tag_ids:
                analytic_tag_ids = [(6, None, self.line_analytic_tag_ids.ids)]

            invoice_line['analytic_tag_ids'] = analytic_tag_ids
            invoice_line['account_analytic_id'] = self.line_analytic_account_id and self.line_analytic_account_id.id or False
            invoice_line['account_id'] = default_account or self.line_account_id.id
            invoice_line['price_subtotal'] = tax_groups[group]['price_subtotal']
            invoice_line['price_unit'] = tax_groups[group]['price_subtotal']
            invoice_line['taxes'] = taxes
            all_products.append(invoice_line)

        return all_products


    def get_company_xml_import_data(self, invoice_type, serie=False):
        """
        -para xmls de cliente
        obtiene el diario, almacen, cuenta analitica
        segun la serie
        -para xmls de proveedor:
        obtiene el diario del wizard
        regresa jorunal_id, analytic_account_id, warehouse_id
        """

        journal_id = False
        analytic_account_id = False
        warehouse_id = False
        bank_id = False
        if invoice_type == 'out_invoice':
            x = 0
            if self.company_id.xml_import_line_ids:
                for line in self.company_id.xml_import_line_ids:

                    if line.xml_import_journal_id.sequence_id.name == serie:
                        journal_id = line.xml_import_journal_id.id
                        analytic_account_id = line.xml_import_analytic_account_id.id
                        warehouse_id = line.xml_import_warehouse_id.id
                        bank_id = line.xml_import_bank_id.id
                        break
                    x += 1
            else:
                # Customer invoice
                journal_id = self.journal_customer_id.id
        else:
            journal_id = self.journal_provider_id.id
            analytic_account_id = self.line_analytic_account_provider_id.id
            warehouse_id = self.warehouse_provider_id and self.warehouse_provider_id.id or False
            bank_id = self.payment_journal_provider_id.id
        #f_logger.info("bank: " + str())
        return journal_id, analytic_account_id, warehouse_id, bank_id