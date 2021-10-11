from odoo import api, fields, models, _
from odoo.exceptions import  Warning
import time
import sys
import stomp
import logging
_logger = logging.getLogger(__name__)


class CmpMessageLog(models.Model):
	_name = "cmp.message.log"
	_description = "CMP message log"
	_rec_name = "id"

	log = fields.Text(readonly=True)