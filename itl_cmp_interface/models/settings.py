from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import paramiko


class CmpConfi(models.TransientModel):
	_inherit = 'res.config.settings'
	

	cmp_host = fields.Char(related="company_id.cmp_host", string="Host", readonly=False)
	cmp_port = fields.Char(related="company_id.cmp_port", string="Port", readonly=False)
	cmp_key_path = fields.Char(related="company_id.cmp_key_path", string="Key path", readonly=False)
	cmp_user = fields.Char(related="company_id.cmp_user", string="User", readonly=False)
	cmp_password = fields.Char(related="company_id.cmp_password", string="Password", readonly=False)
	
	cmp_receiptprintextract_path = fields.Char(related="company_id.cmp_receiptprintextract_path", string="Outbound - Receipt Directory", readonly=False)
	cmp_receiptprintextract_local_path = fields.Char(related="company_id.cmp_receiptprintextract_local_path", string="Inbound - Receipt Directory", readonly=False)
	cmp_recurringprepaymentsextract_path = fields.Char(related="company_id.cmp_recurringprepaymentsextract_path", string="Outbound - Prepayment Directory", readonly=False)
	cmp_recurringprepaymentsextract_local_path = fields.Char(related="company_id.cmp_recurringprepaymentsextract_local_path", string="Inbound - Prepayment Directory", readonly=False)
	cmp_datawarehouse_extracts_path = fields.Char(related="company_id.cmp_datawarehouse_extracts_path", string="Outbound - Datawarehouse Directory", readonly=False)
	cmp_datawarehouse_extracts_local_path = fields.Char(related="company_id.cmp_datawarehouse_extracts_local_path", string="Inbound - Datawarehouse Directory", readonly=False)
	cmp_receipt_path = fields.Char( related="company_id.cmp_receipt_path", string="Inbound – Receipt PDF Directory", readonly=False)
	cmp_recurringprepaymentsextract_inbound_path = fields.Char( related="company_id.cmp_recurringprepaymentsextract_inbound_path", string="Inbound - Recurring Directory", readonly=False)
	cmp_odoo_recurringprepaymentsextract_outbound_path = fields.Char( related="company_id.cmp_odoo_recurringprepaymentsextract_outbound_path", string="Odoo outbound Recurring Directory", readonly=False)
	
	def check_credentials(self):
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		if self.cmp_host or self.cmp_port or self.cmp_user or self.cmp_key_path:
			if self.cmp_host:
				if self.cmp_port:
					if self.cmp_user:
						if self.cmp_key_path:
							try:
								#client.connect(hostname=self.cmp_host, port=self.cmp_port, username=self.cmp_user, key_filename=self.cmp_key_path)
								client.connect(hostname=self.cmp_host, port=self.cmp_port, username=self.cmp_user, password=self.cmp_password, look_for_keys=False)
								client.close()
								message = "Yeah, Connected"
								return {
									'effect': {
									'fadeout': 'fast',
									'message': message,
									'img_url': 'itl_cmp_interface/static/src/img/images_1.jpeg',
									'type': 'rainbow_man',
									}
								}
							except Exception as e:
								raise ValidationError(_("Connection error: " + str(e)))
						else:
							raise ValidationError(_("Set key_filename first"))
					else:
						raise ValidationError(_("Set username first"))
				else:
					raise ValidationError(_("Set port first"))
			else:
				raise ValidationError(_("Set hostname first"))
		else:
			raise ValidationError(_("Set credentials first"))
