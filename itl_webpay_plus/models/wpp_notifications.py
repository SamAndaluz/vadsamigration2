from odoo import _, api, fields, models

import xmltodict
from odoo.addons.itl_webpay_plus.models.AESCrypto import AESCrypto

import logging
_logger = logging.getLogger(__name__)

class WppNotifications(models.Model):
    _name = "wpp.notifications"
    _inherit = ['mail.thread']
    
    response = fields.Char(string="Response", readonly=True)
    decrypted_response = fields.Text(string="Decrypted response", readonly=True)
    invoice_id = fields.Many2one('account.invoice', string="Related invoice", readonly=True)
    status = fields.Selection([('new','New'),('done','Successfully processed'),('error','Processed without success')], default='new')


    def process(self):
        self.decrypt_response()

    def decrypt_response(self):
        if self.response:
            webpay_plus_acquirer_id = self.env['payment.acquirer'].search([('provider', '=', 'webpay_plus')])
            try:
                decriptedString = AESCrypto(webpay_plus_acquirer_id.webpay_plus_key).decrypt(self.response)
                self.decrypted_response = decriptedString
                _logger.info("decriptedString: %s", decriptedString)
                doc = xmltodict.parse(decriptedString)
                
                ref = doc['CENTEROFPAYMENTS']['reference']
                status = doc['CENTEROFPAYMENTS']['response']
                
                # Change A/2020/0010 to ref
                invoice_id = self.env['account.invoice'].search([('number','=',ref)])
                
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
                
                self.invoice_id = invoice_id
                self.status = 'done'
                #return Response(decriptedString,status=200)
            except Exception as e:
                _logger.info("-> Error: " + str(e))
                self.status = 'error'
                self.message_post(body=str(e))

    def create_payment(self, invoice):
        """
        Crea pago para la factura indicada
        """
        AccountRegisterPayments = self.env['account.register.payments'].sudo()
        
        if invoice.type == 'out_invoice':
            journal_id = invoice.with_context({'type': 'out_invoice'})._default_journal()

            payment_type = 'inbound' if invoice.type in ('out_invoice', 'in_refund') else 'outbound'
            if payment_type == 'inbound':
                payment_method = self.env.ref('account.account_payment_method_manual_in')
            else:
                payment_method = self.env.ref('account.account_payment_method_manual_out')

            vals = {
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': journal_id.id,
                'payment_type': payment_type,
                'payment_method_id': payment_method.id,
                'group_invoices': False,
                'invoice_ids': [(6, 0, [invoice.id])],
                'multi': False,
                'payment_date': invoice.date_invoice,
            }
        if invoice.type == 'in_invoice':
            journal_id = invoice.with_context({'type': 'in_invoice'})._default_journal()
            vals = {
                'amount': invoice.amount_total or 0.0,
                'currency_id': invoice.currency_id.id,
                'journal_id': journal_id.id,
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

    def send_mail(self, invoice):
        template_id = self.env.ref('account.email_template_edi_invoice', False)

        if template_id:
            self.env['mail.template'].sudo().browse(template_id.id).send_mail(invoice.id, force_send=True)