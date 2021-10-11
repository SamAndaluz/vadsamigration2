from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import paramiko

class ResCompany(models.Model):
	_inherit = 'res.company'
	
	
	cmp_host = fields.Char(string="Host")
	cmp_port = fields.Char(string="Port")
	cmp_key_path = fields.Char(string="Key path")
	cmp_user = fields.Char(string="User")
	cmp_password = fields.Char(string="Password")

	cmp_receiptprintextract_path = fields.Char(string="Outbound - Receipt Directory")
	cmp_receiptprintextract_local_path = fields.Char(string="Inbound - Receipt Directory")
	cmp_recurringprepaymentsextract_path = fields.Char(string="Outbound - Prepayment Directory")
	cmp_recurringprepaymentsextract_local_path = fields.Char(string="Inbound - Prepayment Directory")
	cmp_datawarehouse_extracts_path = fields.Char(string="Outbound - Datawarehouse Directory")
	cmp_datawarehouse_extracts_local_path = fields.Char(string="Inbound - Datawarehouse Directory")
	cmp_receipt_path = fields.Char(string="Inbound – Receipt PDF Directory")
	cmp_recurringprepaymentsextract_inbound_path = fields.Char(string="Inbound - Recurring Directory")
	cmp_odoo_recurringprepaymentsextract_outbound_path = fields.Char(string="Odoo outbound Recurring Directory")
	


	def check_credentials(self):
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		if self.cmp_host or self.cmp_port or self.cmp_user or self.cmp_key_path:
			if self.cmp_host:
				if self.cmp_port:
					if self.cmp_user:
						if self.cmp_key_path:
							try:
								client.connect(hostname=self.cmp_host, port=self.cmp_port, username=self.cmp_user, password=self.cmp_password, look_for_keys=False)
								client.close()
								return True, ''
							except Exception as e:
								return False, 'Connection error: ' + str(e)
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