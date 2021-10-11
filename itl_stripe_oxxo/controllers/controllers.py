# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import pprint
import werkzeug

import stripe
import json

from odoo.http import route, request
from odoo.addons.payment_stripe_sca.controllers.main import StripeControllerSCA
from odoo.http import Response

import jwt
JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 20

_logger = logging.getLogger(__name__)

class StripeControllerSCAExtend(StripeControllerSCA):


    ####################################################################################################
    ######################## For OXXO payment ##########################################################
    ####################################################################################################
    
    @route('/payment_stripe/oxxo', type='http', auth='public', csrf=False)
    def get_checkout_page_a(self, **kw):
        _logger.info("/payment_stripe/oxxo >>>>> " + str(kw))
        if 'authorization' in kw:
            jwt_token = kw['authorization']
            try:
                payload = jwt.decode(jwt_token, JWT_SECRET,
                                         algorithms=[JWT_ALGORITHM])
            except (jwt.DecodeError, jwt.ExpiredSignatureError) as e:
                return Response("Error: " + str(e), status=403)

            partner_id = request.env['res.partner'].sudo().browse(payload['user_id'])
            invoice_id = request.env['account.invoice'].sudo().browse(payload['invoice_id'])
                
            vals = {
                    'customer_name': partner_id.name,
                    'customer_email': partner_id.email,
                    'invoice_amount': invoice_id.amount_total,
                    'invoice_number': invoice_id.number
                }
                
            return request.render('itl_stripe_oxxo.index_oxxo', vals)
        else:
            return Response("Forbidden", status=403)
    
    @route('/create-payment-intent', type='http', auth='public', csrf=False, method=['POST'])
    def create_payment_intent(self, **kwargs):
        _logger.info("/create-payment-intent >>>>> " + str(kwargs))
        if 'authorization' in kwargs:
            jwt_token = kwargs['authorization']
            try:
                payload = jwt.decode(jwt_token, JWT_SECRET,
                                         algorithms=[JWT_ALGORITHM])
            except (jwt.DecodeError, jwt.ExpiredSignatureError) as e:
                return Response("Error: " + str(e), status=403)
            
            partner_id = request.env['res.partner'].sudo().browse(payload['user_id'])
            invoice_id = request.env['account.invoice'].sudo().browse(payload['invoice_id'])
            
            stripe_acquirer_id = request.env['payment.acquirer'].sudo().search([('provider', '=', 'stripe')])
            if stripe_acquirer_id:
                stripe.api_key = stripe_acquirer_id.stripe_secret_key
                stripe.api_version = '2019-12-03; oxxo_beta=v2'
                metadata = {
                    'invoice_id': invoice_id.id,
                    'invoice_number': invoice_id.number
                }
                description = 'Created from Odoo'
                # Create a PaymentIntent with the order amount and currency
                amount = int(invoice_id.amount_total * 100)
                intent = stripe.PaymentIntent.create(
                    amount=amount,
                    currency='mxn',
                    payment_method_types=['oxxo'],
                    metadata=metadata,
                    description=description
                )
                try:
                    #_logger.info("intent >>>>> " + str(intent))
                    # Send publishable key and PaymentIntent details to client
                    return json.dumps({
                        'publishableKey': stripe_acquirer_id.stripe_publishable_key,
                        'clientSecret': intent.client_secret,
                        'apiVersion': '2019-12-03',
                        'oxxoBetaVersion': 'v2'
                    })
                except Exception as e:
                    #_logger.info("error: " + str(e))
                    return Response("Error: " + str(e), status=400)
            else:
                return Response("No Stripe module instelled in server.", status=400)
        else:
            return Response("Forbidden", status=403)
        
    @route('/webhook', type='json', auth='public', csrf=False, method=['POST'])
    def webhook2_received(self, **kwargs):
        _logger.info('webhook >>>>>')
        payload = request.jsonrequest
        stripe_acquirer_id = request.env['payment.acquirer'].sudo().search([('provider', '=', 'stripe')])
        stripe.api_key = stripe_acquirer_id.stripe_secret_key
        stripe.api_version = '2019-12-03; oxxo_beta=v2'
        event = None

        try:
            event = stripe.Event.construct_from(
              payload, stripe.api_key
            )
            #data = event['data']
            #data_object = data['object']
        except ValueError as e:
            # Invalid payload
            _logger.info('error: ' + str(e))
            return Response(status=400)

          # Handle the event
        if event.type == 'payment_intent.succeeded':
            _logger.info('💰 Payment received!----- >>>>>')
            if 'invoice_id' in event.data.object.metadata:
                _logger.info('invoice id ----- >>>>>')
                invoice_id = event.data.object.metadata.invoice_id
                invoice_id = request.env['account.invoice'].sudo().search([('id','=',invoice_id)])
                _logger.info('invoice id: ' + str(invoice_id))
                
                payment = self.create_payment(invoice_id)
                _logger.info("payment: " + str(payment))
                payment.post()
                _logger.info('payment_post()')
                self.send_mail(invoice_id)
                
        elif event.type == 'payment_intent.payment_failed':
            metadata = event.data.object.metadata # contains a stripe.PaymentIntent
            _logger.info('❌ Payment failed. >>>>>' + str(metadata))
            #_logger.info('payment_method: ' + str(data_object))
          # ... handle other event types
        else:
            # Unexpected event type
            return Response(status=400)

        return Response(status=200)
    
    def send_mail(self, invoice):
        template_id = request.env.ref('account.email_template_edi_invoice', False)
        _logger.info("-> Sending mail")
        _logger.info("-> template_id: " + str(template_id))
        if template_id:
            request.env['mail.template'].sudo().browse(template_id.id).send_mail(invoice.id, force_send=True)
    
    def create_payment(self, invoice):
        """
        Crea pago para la factura indicada
        """
        _logger.info("create_invoice_payment ---->")
        AccountRegisterPayments = request.env['account.register.payments'].sudo()
        _logger.info("out_invoice: " + str(invoice.type))
        if invoice.type == 'out_invoice':
            payment_type = 'inbound' if invoice.type in ('out_invoice', 'in_refund') else 'outbound'
            if payment_type == 'inbound':
                payment_method = request.env.ref('account.account_payment_method_manual_in')
            else:
                payment_method = request.env.ref('account.account_payment_method_manual_out')

            vals = {
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': invoice.journal_id.id,
                'payment_type': payment_type,
                'payment_method_id': payment_method.id,
                'group_invoices': False,
                'invoice_ids': [(6, 0, [invoice.id])],
                'multi': False,
                'payment_date': invoice.date_invoice,
            }
        if invoice.type == 'in_invoice':
            vals = {
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': invoice.journal_id.id,
                'payment_type': False,
                'payment_method_id': False,
                'group_invoices': False,
                'invoice_ids': [(6, 0, [invoice.id])],
                'multi': False,
                'payment_date': invoice.date_invoice,
            }
        account_register_payment_id = AccountRegisterPayments.with_context({'active_ids': [invoice.id, ]}).sudo().create(vals)
        payment_vals = account_register_payment_id.get_payments_vals()

        AccountPayment = request.env['account.payment'].sudo()
        return AccountPayment.create(payment_vals)
    
    """
    @route('/webhook2', type='json', auth='public', csrf=False, method=['POST'])
    def webhook_received(self, **post):
        # You can use webhooks to receive information about asynchronous payment events.
        # For more about our webhook events check out https://stripe.com/docs/webhooks.
        request_data = request.jsonrequest
        _logger.info("webhook_received: " + str(request_data))
        stripe_acquirer_id = request.env['payment.acquirer'].sudo().search([('provider', '=', 'stripe')])
        
        if stripe_acquirer_id:
            webhook_secret = "whsec_EHCgZd9mAdeSXPOI7ValghVIM0W6C04E"

            if webhook_secret:
                #_logger.info("header: " + str(header.get('HTTP_SEC_FETCH_SITE')))
                # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
                signature = request.httprequest.headers.environ.get('HTTP_STRIPE_SIGNATURE')
                #_logger.info("signature: " + str(signature))
                try:
                    event = stripe.Webhook.construct_event(request_data, signature, webhook_secret)
                    data = event['data']
                except Exception as e:
                    _logger.info("exception: " + str(e))
                    return Response("error: " + str(e), status=400)
                # Get the type of webhook event sent - used to check the status of PaymentIntents.
                event_type = event['type']
            else:
                data = request_data['data']
                event_type = request_data['type']
            data_object = data['object']

            if event_type == 'payment_intent.succeeded':
                print('💰 Payment received!')
                # Fulfill any orders, e-mail receipts, etc
                # To cancel the payment you will need to issue a Refund (https://stripe.com/docs/api/refunds)
            elif event_type == 'payment_intent.payment_failed':
                print('❌ Payment failed.')
            return Response("Success", status=200)
        else:
            return Response("No Stripe module instelled in server.", status=400)
    """
    """
    @route('/webhook3', type='json', auth='public', csrf=False, method=['POST'])
    def webhook3_received(self, **kwargs):
        payload = request.jsonrequest
        #_logger.info('payload: ' + str(payload))
        stripe_acquirer_id = request.env['payment.acquirer'].sudo().search([('provider', '=', 'stripe')])
        stripe.api_key = stripe_acquirer_id.stripe_secret_key
        
        sig_header = request.httprequest.headers.environ.get('HTTP_STRIPE_SIGNATURE')
        event = None
        endpoint_secret = "whsec_EHCgZd9mAdeSXPOI7ValghVIM0W6C04E"

        try:
            event = stripe.Webhook.construct_event(
              payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            # Invalid payload
            return Response(status=400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            _logger.info('error: ' + str(e))
            return Response(status=400)

          # Handle the event
        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object # contains a stripe.PaymentIntent
            _logger.info('PaymentIntent was successful!')
        elif event.type == 'payment_method.attached':
            payment_method = event.data.object # contains a stripe.PaymentMethod
            _logger.info('PaymentMethod was attached to a Customer!')
        # ... handle other event types
        else:
            # Unexpected event type
            return Response(status=400)

        return Response(status=200)
    """
    