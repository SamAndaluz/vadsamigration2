# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2020-today Ascetic Business Solution <http://www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################
from odoo import _, api, fields, models
import requests
import xmltodict
import pprint
import json
import logging
import base64
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError
from xml.etree.ElementTree import XML, fromstring
import xml.etree.ElementTree as ET
from xml.etree import ElementTree
from io import StringIO
from lxml import etree
from odoo.http import route, request
from odoo.addons.payment_stripe_sca.controllers.main import StripeControllerSCA
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, \
    pycompat, date_utils

import jwt
JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 300


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    stripe_payment_ref = fields.Text("Payment Reference")

    def send_oxxo_link(self):
        _logger.info("oxxo_link")
        if self.partner_id and self.journal_id:
            if self.journal_id.name:
                stripe_oxxo_acquirer_id = self.env['payment.acquirer'].search([('provider', '=', 'stripe')])
                if stripe_oxxo_acquirer_id:
                    if not stripe_oxxo_acquirer_id.stripe_current_host:
                        raise ValidationError("Current host is not configured in Stripe configuration.")

                    payload = {
                                'user_id': self.partner_id.id,
                                'invoice_id': self.id,
                                'invoice_number': self.number
                                #'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
                            }
                    jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
                    #_logger.info("token: " + str(jwt_token.decode('utf-8')))
                    if self.partner_id.email and jwt_token:
                        mail = {}
                        email_subject = str(self.partner_id.name) + " - Please, Pay your bill regarding" + self.number + " ."
                        url = stripe_oxxo_acquirer_id.stripe_current_host + "/payment_stripe/oxxo?authorization={0}".format(jwt_token.decode('utf-8'))
                        mail_contain = """Hello {0}, <p>Kindly click on the <a style="display:inline-block;font-weight:700;background-color:#00A09D;color: #FFFFFF;padding: 14px 25px;text-align: center;text-decoration: none;font-size:16px;margin-bottom:10px;opacity:0.9;" target="_blank" href='{1}' class="btn_pago">Payment</a> to do the payment of {2}  with the amount {3}.</p> Regards,<br/>{4}""".format(
                            str(self.partner_id.name), url, str(self.number), str(self.amount_total) + self.currency_id.symbol, self.env.user.name)
                        mail_create = self.env['mail.mail'].create({
                            'subject': email_subject,
                            'email_from': self.env.user.email,
                            'recipient_ids': [(6, 0, [self.partner_id.id])],
                            'body_html': mail_contain,
                            'auto_delete': False
                        })
                        _logger.info("mail_create >>>>>>>>>" + str(mail_create))
                        if mail_create:
                            mail_create.send()
