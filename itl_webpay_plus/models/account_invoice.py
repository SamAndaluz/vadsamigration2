
import subprocess
import urllib.parse
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, pycompat, date_utils
from odoo.addons.payment_stripe_sca.controllers.main import StripeControllerSCA
from odoo.http import route, request
from lxml import etree
from io import StringIO
from xml.etree import ElementTree
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import XML, fromstring
from odoo.exceptions import UserError, ValidationError
from odoo import _, api, fields, models
import requests
import pprint
import json
import logging
import base64
from datetime import datetime
_logger = logging.getLogger(__name__)

from odoo.addons.itl_webpay_plus.models.AESCrypto import AESCrypto

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def send_wpp_link(self):
        _logger.info(">>>>>>Function Call>>>>>>>action_validate_invoice_payment>>>>>")
        #key = "5dcc67393750523cd165f17e1efadd21"
        #unpad = lambda s : s[:-s[-1]]
        #key = unhexlify(key)
        if self.partner_id and self.journal_id:
            if self.journal_id.name:
                webpay_plus_acquirer_id = self.env['payment.acquirer'].search([('provider', '=', 'webpay_plus')])
                _logger.info(">>>>>> webpay_plus_acquirer_id >>>>>>>: " + str(webpay_plus_acquirer_id))
                if webpay_plus_acquirer_id:
                    _logger.info(">>>>>> in if >>>>>>>")
                    # Was removed from <url> <promociones>C,3,6,9</promociones> </url>
                    xcd_string = """
                        <P>
                          <business>
                            <id_company>{0}</id_company>
                            <id_branch>{1}</id_branch>
                            <user>{2}</user>
                            <pwd>{3}</pwd>
                          </business>
                          <url>
                            <reference>{4}</reference>
                            <amount>{5}</amount>
                            <moneda>MXN</moneda>
                            <canal>W</canal>
                            <omitir_notif_default>1</omitir_notif_default>
                            <st_correo>1</st_correo>
                            <mail_cliente>{6}</mail_cliente>
                            <datos_adicionales>
                              <data id="1" display="true">
                                <label>Size</label>
                                <value>Large</value>
                              </data>
                              <data id="2" display="false">
                                <label>Color</label>
                                <value>Blue</value>
                              </data>
                            </datos_adicionales>
                          </url>
                        </P>""".format(webpay_plus_acquirer_id.webpay_plus_company, webpay_plus_acquirer_id.webpay_plus_branch, webpay_plus_acquirer_id.webpay_plus_user, webpay_plus_acquirer_id.webpay_plus_pwd, self.number, self.amount_total, self.partner_id.email)

                    #local_path = webpay_plus_acquirer_id.local_path
                    #_logger.info(">>>>>localpath>>>>>>>>>>: " + str(local_path))
                    #result = subprocess.run(
                    #    ['php', local_path + '/encrypt.php', local_path + '/AESCrypto.php', xcd_string],    # program and arguments
                    #    stdout=subprocess.PIPE,  # capture stdout
                    #)
                    #script_response = result.stdout.decode('utf-8')
                    script_response = AESCrypto(webpay_plus_acquirer_id.webpay_plus_key).encrypt2(xcd_string).decode('utf-8')
                    #_logger.info(">>>>>xcd_string>>>>>>>>>>" + str(xcd_string))
                    # Sandbox
                    #xml = """<pgs><data0>SNDBX123</data0><data>""" + script_response + """</data></pgs>"""
                    xml = ("""<pgs><data0>{0}</data0><data>""" + script_response + """</data></pgs>""").format(webpay_plus_acquirer_id.webpay_plus_data0)
                    #_logger.info(">>>>> xml >>>>>>>>>>" + str(xml))
                    # For Sandbox
                    #urequest = requests.post("https://wppsandbox.mit.com.mx/gen?" + str(urllib.parse.urlencode({'xml': xml})), headers={'Content-Type': 'application/x-www-form-urlencoded', "cache-control": "no-cache"}, )
                    urequest = requests.post(str(webpay_plus_acquirer_id.webpay_plus_endpoint) + "?" + str(urllib.parse.urlencode({'xml': xml})), headers={'Content-Type': 'application/x-www-form-urlencoded', "cache-control": "no-cache"}, )
                    resp = ""
                    decrypted_string = ""
                    _logger.info(">>>>>request.status_code>>>>>>>>>> status:" + str(urequest.status_code) + " - text: " + str(urequest.text))
                    if urequest.status_code == 200:
                        resp = urequest.text
                        #_logger.info(">>>>> resp >>>>>>>>>>" + str(resp))
                        
                        #decrypt_result = subprocess.run(
                        #    ['php', local_path + '/decrypt.php', local_path + '/AESCrypto.php', resp],    # program and arguments
                        #    stdout=subprocess.PIPE,  # capture stdout
                        #)
                        #decrypt_script_response = decrypt_result.stdout.decode(
                        #    'utf-8')
                        decrypt_script_response = AESCrypto(webpay_plus_acquirer_id.webpay_plus_key).decrypt(resp)
                        #_logger.info(">>>>>decrypt_script_response>>>>>>>>>>" + str(decrypt_script_response))
                        #raise ValidationError("ok")
                        decrypted_string = decrypt_script_response.split("<nb_url>")[1].split("</nb_url>")[0]
                    else:
                        decrypted_string = None
                    #_logger.info(">>>>>decrypted_string>>>>>>>>>" + str(decrypted_string))
                    mail = {}
                    email_subject = str(
                        self.partner_id.name) + " - Please, Pay your bill regarding" + str(self.number) + " ."
                    if self.partner_id.email and self.env.uid and decrypted_string:
                        mail_contain = """Hello {0}, <p>Kindly click on the <a style="display:inline-block;font-weight:700;background-color:#f44336;color: #FFFFFF;padding: 14px 25px;text-align: center;text-decoration: none;font-size:16px;margin-bottom:10px;opacity:0.9;" target="_blank" href='{1}' class="btn_pago">Payment</a> to do the payment of {2}  with the amount {3}.</p> Regards,<br/>{4}""".format(
                            str(self.partner_id.name), decrypted_string, str(self.number), str(self.amount_total) + self.currency_id.symbol, self.env.user.name)
                        mail_create = self.env['mail.mail'].create({
                            'subject': email_subject,
                            'email_from': self.env.user.email,
                            'recipient_ids': [(6, 0, [self.partner_id.id])],
                            'body_html': mail_contain,
                            'auto_delete': False
                        })
                        _logger.info(">>>>>mail_create>>>>>>>>>" + str(mail_create))
                        if mail_create:
                            mail_create.send()
                            self.message_post(body="Payment link was send to customer email.")
                else:
                    self.message_post(body="The payment acquirer WebPay Plus is not installed.")
                    _logger.info(">>>>>no webpay_plus_acquirer_id>>>>>>>>>")
                    
        