
import pprint
import logging
from werkzeug import urls, utils

from odoo import http
from odoo.http import request
_logger = logging.getLogger(__name__)

from xml.etree.ElementTree import XMLParser

import json
import requests
import werkzeug
from werkzeug import urls

from odoo import http, tools, _
from odoo.http import Response
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.exceptions import ValidationError
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.addons.website_sale.controllers.main import WebsiteSale, TableCompute
from odoo.addons.itl_webpay_plus.models.AESCrypto import AESCrypto

from base64 import b64decode
from base64 import b64encode
import base64
from Crypto import Random
from Crypto.Cipher import AES
import random

block_size = AES.block_size

from binascii import hexlify, unhexlify
from urllib.parse import unquote

import xmltodict

class WPPAuthorityController(http.Controller):

    @http.route(['/odoo/webpayplus/response'], auth="public", methods=['POST'], website=True, csrf=False)
    def index(self, **post):
        _logger.info("-> entrando a /odoo/webpayplus/response")
        webpay_plus_acquirer_id = request.env['payment.acquirer'].sudo().search([('provider', '=', 'webpay_plus')])
        response = post['strResponse']
        rec = request.env['wpp.notifications'].sudo().create({'response': response})
        #_logger.info("decriptedString: %s", response)
        try:
            decriptedString = AESCrypto(webpay_plus_acquirer_id.webpay_plus_key).decrypt(response)
            _logger.info("decriptedString: %s", decriptedString)
            doc = xmltodict.parse(decriptedString)
            
            ref = doc['CENTEROFPAYMENTS']['reference']
            status = doc['CENTEROFPAYMENTS']['response']
            
            # Change A/2020/0010 to ref
            invoice_id = request.env['account.invoice'].sudo().search([('number','=',ref)])
            
            if status == 'approved':
                if invoice_id:
                    number_tkn = False
                    if 'number_tkn' in doc['CENTEROFPAYMENTS']:
                        number_tkn = doc['CENTEROFPAYMENTS']['number_tkn']
                        invoice_id.partner_id.token_wpp_ids = [(0, 0, {'cardToken': number_tkn})]

                if invoice_id.state == 'open':
                    payment = self.create_payment(invoice_id)
                    payment.post()
                    self.send_mail(invoice_id)
                    invoice_id.message_post(body="WebPay Plus payment APPROVED.")
                    
            if status == 'denied':
                if invoice_id:
                    invoice_id.message_post(body="WebPay Plus payment DENIED, please use another card.")
            if status == 'error':
                if invoice_id:
                    invoice_id.message_post(body="WebPay Plus payment ERROR, please contact MIT Customer Service.")
            
            #return Response(decriptedString,status=200)
        except Exception as e:
            _logger.info("-> Error: " + str(e))
            rec.message_post(body=str(e))
    
    def send_mail(self, invoice):
        template_id = request.env.ref('account.email_template_edi_invoice', False)

        if template_id:
            request.env['mail.template'].sudo().browse(template_id.id).send_mail(invoice.id, force_send=True)
    
    def create_payment(self, invoice):
        """
        Crea pago para la factura indicada
        """
        AccountRegisterPayments = request.env['account.register.payments'].sudo()
        _logger.info("out_invoice: %s", invoice.type)
        if invoice.type == 'out_invoice':
            payment_type = 'inbound' if invoice.type in ('out_invoice', 'in_refund') else 'outbound'
            if payment_type == 'inbound':
                payment_method = request.env.ref('account.account_payment_method_manual_in')
            else:
                payment_method = request.env.ref('account.account_payment_method_manual_out')

            vals = {
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': 24,
                'payment_type': payment_type,
                'payment_method_id': payment_method.id,
                'group_invoices': False,
                'invoice_ids': [(6, 0, [invoice.id])],
                'multi': False,
                'payment_date': invoice.date_invoice,
                'company_id': invoice.company_id.id
            }
        if invoice.type == 'in_invoice':
            vals = {
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': 24,
                'payment_type': False,
                'payment_method_id': False,
                'group_invoices': False,
                'invoice_ids': [(6, 0, [invoice.id])],
                'multi': False,
                'payment_date': invoice.date_invoice,
                'company_id': invoice.company_id.id
            }
        account_register_payment_id = AccountRegisterPayments.with_context({'active_ids': [invoice.id, ]}).sudo().create(vals)
        payment_vals = account_register_payment_id.get_payments_vals()

        AccountPayment = request.env['account.payment'].sudo()
        return AccountPayment.create(payment_vals)