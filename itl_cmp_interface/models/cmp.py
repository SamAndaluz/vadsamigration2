from odoo import api, fields, models, _
import paramiko
import os
import json
from jsonschema import validate
import jsonschema
from datetime import date
from datetime import datetime, timedelta
import subprocess
import base64
import paramiko
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_resource
recurring_payment_rejection_schema_path = get_module_resource('itl_cmp_interface', 'data/', 'recurringprepaymentscardrejections.schema.json')
import pytz
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging
_logger = logging.getLogger(__name__)

response_codes = ['00','01','02','04','05','06','07','12','13','14','36','41','43','51','57','62','78','84','100','101','200','T5','15','45','46','48','80','82','83','87','94','N0','R1','03','30','52','61','65','N8','O8','P1','T4','34','35','37','56','Q5','N7','N6']

class CmpMessage(models.Model):
	_name = "cmp.message"
	_inherit = ['mail.thread']
	_description = "CMP message"
	_rec_name = "id"

	def _get_default_company(self):
		param = self.env['ir.config_parameter'].sudo()
		sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
		company_id = False
		if sr_company_id:
			company_id = self.env['res.company'].browse(int(sr_company_id))
		
		return company_id

	name = fields.Char("Type")
	status_file = fields.Selection([('new','Nuevo'),
								('sent','Enviado a ELAVON'),
								('done','Todos aprobados'),
								('partial','Algunos rechazados'),
								('error','Error al procesar'),
								('to_send_tomorrow','To send tomorrow'),
								('sent_rejection','Enviado a CMP'),
								('no_data','Sin datos')], copy=False, compute="_get_file_status")
	status = fields.Selection([('new','Nuevo'),
								('sent','Enviado a ELAVON'),
								('done','Todos aprobados'),
								('partial','Algunos rechazados'),
								('sent_rejection','Enviado a CMP'),
								('error','Error al procesar'),
								('response_error','Error al procesar respuesta'),
								('no_data','Sin datos')], copy=False)
	status_amex = fields.Selection([('new','Nuevo'),
								('sent','Enviado a ELAVON'),
								('done','Todos aprobados'),
								('partial','Algunos rechazados'),
								('sent_rejection','Enviado a CMP'),
								('error','Error al procesar'),
								('to_send_tomorrow','To send tomorrow'),
								('response_error','Error al procesar respuesta'),
								('no_data','Sin datos')], copy=False)
	status_message = fields.Selection([('all_ok','Todo correcto'),
										('warning','Revisar'),
										('no_data','Sin datos')], copy=False, compute="_get_general_status")
	message_id = fields.Char(string="Message ID")
	file = fields.Binary(string="CMP file")
	file_name = fields.Char('File Name')
	content_file = fields.Text()
	job_code = fields.Char(string="jobCode")
	job_description = fields.Char(string="jobDescription")
	batch_date_time = fields.Datetime(string="batchDateTime")
	file_to_elavon = fields.Binary(string="File Visa/MasterCard to Elavon")
	filename_to_elavon = fields.Char('File Name')
	file_amex_to_elavon = fields.Binary(string="File American Express to Elavon")
	filename_amex_to_elavon = fields.Char('File Name')
	file_from_elavon = fields.Binary(string="File Visa/MasterCard from Elavon")
	filename_from_elavon = fields.Char('File Name')
	file_from_elavon_err = fields.Binary(string="File Visa/MasterCard from Elavon Err")
	filename_from_elavon_err = fields.Char('File Name')
	file_amex_from_elavon = fields.Binary(string="File Amex from Elavon")
	filename_amex_from_elavon = fields.Char('File Name')
	file_amex_from_elavon_err = fields.Binary(string="File Amex from Elavon Err")
	filename_amex_from_elavon_err = fields.Char('File Name')
	file_rejection_to_cmp = fields.Binary(string="Rejection file to CMP")
	filename_file_rejection_to_cmp = fields.Char('File name')
	company_id = fields.Many2one('res.company', string="Compañía", readonly=True, store=True, default=_get_default_company)
	send_tomorrow = fields.Boolean(string="Send tomorrow")
	datetime_to_send = fields.Datetime(string="Datetime to send")

	cmp_item_ids = fields.One2many('cmp.item', 'cmp_message_id', string="CMP Items", readonly=True)

	@api.depends('status','status_amex')
	def _get_general_status(self):
		for m in self:
			m.status_message = False
			if m.status == 'sent' or m.status_amex == 'sent':
				m.status_message = 'all_ok'
			if m.status == 'done' and m.status_amex in ['done', False]:
				m.status_message = 'all_ok'
			if m.status_amex == 'done' and m.status in ['done', False]:
				m.status_message = 'all_ok'
			if m.status == 'sent_rejection' or m.status_amex == 'sent_rejection':
				m.status_message = 'warning'
			if (m.status == 'partial' or m.status_amex == 'partial') and not m.file_rejection_to_cmp:
				m.status_message = 'warning'
			if (m.status == 'partial' or m.status_amex == 'partial') and m.file_rejection_to_cmp:
				m.status_message = 'warning'
			if m.status == False and m.status_amex == False:
				m.status_message = 'no_data'
			if len(m.cmp_item_ids) > 0:
				for d in m.cmp_item_ids:
					if not d.invoice_id:
						m.status_message = 'warning'
						break

	@api.depends('status','status_amex')
	def _get_file_status(self):
		for m in self:
			m.status_file = False
			if m.status == 'sent' or m.status_amex == 'sent':
				m.status_file = 'sent'
			if m.status == 'done' and m.status_amex in ['done', False]:
				m.status_file = 'done'
			if m.status_amex == 'done' and m.status in ['done', False]:
				m.status_file = 'done'
			if m.status == 'sent_rejection' or m.status_amex == 'sent_rejection':
				m.status_file = 'sent_rejection'
			if (m.status == 'partial' or m.status_amex == 'partial') and not m.file_rejection_to_cmp:
				m.status_file = 'partial'
			if (m.status == 'partial' or m.status_amex == 'partial') and m.file_rejection_to_cmp:
				m.status_file = 'sent_rejection'
			if m.status == False and m.status_amex == False:
				m.status_file = 'no_data'


	def process_details(self):
		if len(self.cmp_item_ids) > 0:
			param = self.env['ir.config_parameter'].sudo()
			sr_company_id = param.get_param('itl_sr_interface.sr_company_id') or False
			elavon_id_buzon = param.get_param('itl_elavon_cron.elavon_id_buzon') or False
			elavon_id_company = param.get_param('itl_elavon_cron.elavon_id_company') or False
			elavon_local_outbox_path = param.get_param('itl_elavon_cron.elavon_local_outbox_path') or False
			error_flag = False
			if not sr_company_id:
				self.message_post(body="Advertencia: No está configurada la compañía.", subject="Registro no procesado")
				self.status_file = 'error'
				return
			file_lines_vm = []
			file_lines_am = []
			cmp_item_ids = self.cmp_item_ids.filtered(lambda i: i.status == 'new')
			if len(cmp_item_ids) == 0:
				self.message_post(body="Advertencia: Ningún item para procesar.", subject="Registro no procesado")
				self.status_file = 'error'
				return
			for detail in cmp_item_ids:
				has_subscription = True
				has_subscription_product = True
				if not detail.account_number:
					self.message_post(body="Advertencia: El item " + str(detail.transaction_number) + " no tiene account number.", subject="Registro no procesado")
					detail.message_post(body="Advertencia: El item " + str(detail.transaction_number) + " no tiene account number.", subject="Registro no procesado")
					self.status_file = 'error'
					detail.status = 'error'
					error_flag = True
					continue
				_logger.info("-> detail.account_number: ***" + str(detail.account_number) + "**")
				_logger.info("-> sr_company_id: " + str(sr_company_id))
				sale_subscription_id = self.env['sale.subscription'].with_context(force_company=sr_company_id).search([('account_id_ref','=',detail.account_number),('company_id.id','=',sr_company_id)], limit=1)
				_logger.info("-> sale_subscription_id: " + str(sale_subscription_id))
				if not sale_subscription_id:
					self.message_post(body="Advertencia: No se creó la factura. No se encontró la suscripción asociada al account number " + str(detail.account_number) + " en el item " + str(detail.transaction_number), subject="Registro no procesado")
					detail.message_post(body="Advertencia: No se creó la factura. No se encontró la suscripción asociada al account number " + str(detail.account_number) + " en el item " + str(detail.transaction_number), subject="Registro no procesado")
					self.status_file = 'error'
					#detail.status = 'error'
					has_subscription = False
					error_flag = True
					#continue
				if detail.amount == 0.0:
					self.message_post(body="Advertencia: No se creó la factura. El valor del detalle es 0 en el item " + str(detail.transaction_number), subject="Registro no procesado")
					detail.message_post(body="Advertencia: No se creó la factura. El valor del detalle es 0 en el item " + str(detail.transaction_number), subject="Registro no procesado")
					self.status_file = 'error'
					error_flag = True
					#detail.status = 'error'
					#continue
				# Revisa si la suscripción tiene un producto de tipo Plan, sino no se crea la factura y regresa mensaje de error
				product_plan = sale_subscription_id.recurring_invoice_line_ids.filtered(lambda line: line.product_id.isRecurring or 'Recurrente' in line.product_id.name)
				if len(product_plan) == 0:
					self.message_post(body="Advertencia: No se creó la factura. La suscripción asociada al account number " + str(detail.account_number) + " no tiene un producto de tipo Plan recurrente.", subject="Registro no procesado")
					detail.message_post(body="Advertencia: No se creó la factura. La suscripción asociada al account number " + str(detail.account_number) + " no tiene un producto de tipo Plan recurrente.", subject="Registro no procesado")
					self.status_file = 'error'
					#detail.status = 'error'
					has_subscription_product = False
					error_flag = True
					#continue
				#product_plan = product_plan[-1]
				if len(product_plan) > 1:
					self.message_post(body="Advertencia: No se creó la factura. La suscripción asociada al account number " + str(detail.account_number) + " tiene más de un producto de tipo Plan recurrente.", subject="Registro no procesado")
					detail.message_post(body="Advertencia: No se creó la factura. La suscripción asociada al account number " + str(detail.account_number) + " tiene más de un producto de tipo Plan recurrente.", subject="Registro no procesado")
					self.status_file = 'error'
					error_flag = True
					#detail.status = 'error'
					has_subscription_product = False
					#continue
				total_amount = float(detail.amount)
				total_untaxed_amount = float(total_amount) / 1.16
				try:
					total_amount = "%.2f" % round(abs(total_amount), 2)
					ref = ""
					email = ""
					invoice_id = False
					if has_subscription and has_subscription_product:
						invoice_id = sale_subscription_id.with_context({'price_unit': total_untaxed_amount})._recurring_create_invoice()
						ref = str(invoice_id.id)
						email = invoice_id.partner_id.email
					else:
						ref = "none"
					if sale_subscription_id and sale_subscription_id.partner_id:
						email = sale_subscription_id.partner_id.email

					if len(detail.card_reference_number) == 15:
						file_line = (str(detail.id) + '_' + str(ref)) + '\t' + str(detail.card_reference_number) + '\t' + str(total_amount) + '\t' + str(email)
						file_lines_am.append(file_line)
					else:
						file_line = (str(detail.id) + '_' + str(ref)) + '\t' + str(detail.card_reference_number) + '\t' + str(total_amount) + '\t' + str(email) + '\t' + str(detail.account_number)
						file_lines_vm.append(file_line)
					
					if invoice_id:
						detail.invoice_id = invoice_id.id
						detail.message_post(body="La factura se creó correctamente.", subject="Registro procesado")
				except Exception as e:
					self.message_post(body="Exception: " + str(e.args[0]), subject="Registro no procesado")
					detail.message_post(body="Exception: " + str(e.args[0]), subject="Registro no procesado")
					self.status_file = 'error'
					detail.status = 'error'
					error_flag = True
					continue
			if len(file_lines_vm) > 0:
				elavon_message = '\n'.join(file_lines_vm)
				datetime_object = datetime.now()
				#today_1pm = datetime_object.replace(hour=13, minute=0, second=0, microsecond=0)
				date_tz = pytz.UTC.localize(datetime.strptime(str(fields.Datetime.now()), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(timezone('America/Mexico_City'))
				#send_tomorrow = False
				#_logger.info("===***> date_tz: " + str(date_tz.time()))
				#_logger.info("===***> today_1pm: " + str(today_1pm.time()))
				#if date_tz.time() > today_1pm.time():
				#	_logger.info("La fecha es mayor a la 1 pm: " + str(date_tz))
				#	tomorrow_date = date_tz + timedelta(days=1)
				#	filename = "pcv" + str(elavon_id_company) + str(elavon_id_buzon) + str(tomorrow_date.year)[-2:] + str('{:02d}'.format(tomorrow_date.month)) + str('{:02d}'.format(tomorrow_date.day)) + str('{:02d}'.format('01')) + str('{:02d}'.format('00')) + str("_token.txt")
				#	send_tomorrow = True
				#	self.send_tomorrow = send_tomorrow
				#	self.datetime_to_send = datetime(tomorrow_date.year, tomorrow_date.month, tomorrow_date.day, '01', '00', '00')
				#else:
				#	_logger.info("La fecha es menor a la 1 pm: " + str(date_tz))
				filename = "pcv" + str(elavon_id_company) + str(elavon_id_buzon) + str(date_tz.year)[-2:] + str('{:02d}'.format(date_tz.month)) + str('{:02d}'.format(date_tz.day)) + str('{:02d}'.format(date_tz.hour)) + str('{:02d}'.format(date_tz.minute)) + str("_token.txt")
				#raise ValidationError("Testing...")
				with open(str(elavon_local_outbox_path) + "/" + str(filename), 'w') as file:
					file.write(elavon_message)
				file_content_binary = open(elavon_local_outbox_path + '/' + str(filename), 'rb')
				file_content = file_content_binary.read()
				file_b64 = base64.b64encode(file_content)
				self.file_to_elavon = file_b64
				self.filename_to_elavon = filename
				#if not send_tomorrow:
				try:
					self.send_to_elavon(self.filename_to_elavon)
					_logger.info("###### PASÓ send_to_elavon VM")
					self.status = 'sent'
					self.status_file = 'sent'
					for detail in self.cmp_item_ids:
						if not detail.status or not detail.status == 'error':
							detail.status = 'sent'
				except Exception as e:
					self.message_post(body="Exception: " + str(e), subject="Registro no procesado")
					self.status = 'error'
					error_flag = True
					
			if len(file_lines_am) > 0:
				elavon_message = '\n'.join(file_lines_am)
				datetime_object = datetime.now()
				today_1pm = datetime_object.replace(hour=13, minute=0, second=0, microsecond=0)
				date_tz = pytz.UTC.localize(datetime.strptime(str(fields.Datetime.now()), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(timezone('America/Mexico_City'))
				send_tomorrow = False
				#_logger.info("===***> date_tz: " + str(date_tz.time()))
				#_logger.info("===***> today_1pm: " + str(today_1pm.time()))
				#if False:
				if date_tz.time() > today_1pm.time():
					_logger.info("La fecha es mayor a la 1 pm: " + str(date_tz))
					tomorrow_date = date_tz + timedelta(days=1)
					filename = "pca" + str(elavon_id_company) + str(elavon_id_buzon) + str(tomorrow_date.year)[-2:] + str('{:02d}'.format(tomorrow_date.month)) + str('{:02d}'.format(tomorrow_date.day)) + str('{:02d}'.format(1)) + str('{:02d}'.format(0)) + str("_token.txt")
					send_tomorrow = True
					self.send_tomorrow = send_tomorrow
					self.datetime_to_send = datetime(tomorrow_date.year, tomorrow_date.month, tomorrow_date.day, 1, 0, 0)
				else:
					_logger.info("La fecha es menor a la 1 pm: " + str(date_tz))
					filename = "pca" + str(elavon_id_company) + str(elavon_id_buzon) + str(date_tz.year)[-2:] + str('{:02d}'.format(date_tz.month)) + str('{:02d}'.format(date_tz.day)) + str('{:02d}'.format(date_tz.hour)) + str('{:02d}'.format(date_tz.minute)) + str("_token.txt")
				with open(str(elavon_local_outbox_path) + "/" + str(filename), 'w') as file:
					file.write(elavon_message)
				file_content_binary = open(elavon_local_outbox_path + '/' + str(filename), 'rb')
				file_content = file_content_binary.read()
				file_b64 = base64.b64encode(file_content)
				self.file_amex_to_elavon = file_b64
				self.filename_amex_to_elavon = filename
				if not send_tomorrow:
					try:
						self.send_to_elavon(self.filename_amex_to_elavon)
						self.status_amex = 'sent'
						self.status_file = 'sent'
						for detail in self.cmp_item_ids:
							detail.status = 'sent'
					except Exception as e:
						self.message_post(body="Exception: " + str(e.args[0]), subject="Registro no procesado")
						self.status_amex = 'error'
						error_flag = True
				else:
					self.status_amex = 'to_send_tomorrow'
					self.status_file = 'to_send_tomorrow'
			if error_flag:
				self.status_message = 'warning'
			else:
				self.status_message = 'all_ok'
			if len(file_lines_vm) == 0 and len(file_lines_am) == 0:
				self.message_post(body="Advertencia: No se crearon líneas para el archivo.", subject="Registro no procesado")
				self.status_file = 'error'
				return
		else:
			self.message_post(body="Advertencia: El archivo no tiene detalles.", subject="Registro no procesado")
			self.status_file = 'no_data'
			return

	def send_pendings_to_elavon(self):
		cmp_files = self.env['cmp.message'].search([('send_tomorrow','=',True)])
		for cmp_f in cmp_files:
			#datetime_to_send = pytz.UTC.localize(datetime.strptime(str(cmp_f.datetime_to_send), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(timezone('America/Mexico_City'))
			datetime_to_send = cmp_f.datetime_to_send
			today = pytz.UTC.localize(datetime.strptime(str(fields.Datetime.now()), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(timezone('America/Mexico_City'))
			_logger.info(" ==**> send_pendings_to_elavon - datetime_to_send: " + str(datetime_to_send.date()))
			_logger.info(" ==**> send_pendings_to_elavon - today: " + str(today.date()))
			if today.date() == datetime_to_send.date():
				_logger.info("***==> ENTRÓ ======")
				_logger.info("***==>  filename_amex_to_elavon: " + str(cmp_f.filename_amex_to_elavon))
				if cmp_f.file_amex_to_elavon:
					try:
						cmp_f.send_to_elavon(cmp_f.filename_amex_to_elavon)
						_logger.info("***==> DESPUÉS DE send_to_elavon ======")
					except Exception as e:
						cmp_f.message_post(body="Exception: " + str(e.args[0]), subject="Registro no procesado")
						cmp_f.status_amex = 'error'
						return
					cmp_f.status_amex = 'sent'
					cmp_f.status_file = 'sent'
					for detail in cmp_f.cmp_item_ids:
						detail.status = 'sent'
		pass

	def send_to_elavon(self, filename):
		ICPSudo = self.env['ir.config_parameter'].sudo()
		elavon_hostname = ICPSudo.get_param('itl_elavon_cron.elavon_hostname') or False
		elavon_port = ICPSudo.get_param('itl_elavon_cron.elavon_port') or False
		elavon_user = ICPSudo.get_param('itl_elavon_cron.elavon_user') or False
		elavon_password = ICPSudo.get_param('itl_elavon_cron.elavon_password') or False
		elavon_local_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_outbox_path') or False
		elavon_remote_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_inbox_path') or False
		try:
			client = paramiko.SSHClient()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			client.connect(hostname=elavon_hostname, port=elavon_port, username=elavon_user, password=elavon_password)
			ftp_client = client.open_sftp()
			ftp_client.chdir("/")
			ftp_client.put(str(elavon_local_outbox_path) + "/" + str(filename), str(elavon_remote_inbox_path) + "/" + str(filename))
			self.message_post(body="El archivo " + str(filename) + " se envió correctamente a ELAVON.", subject="Registro procesado")
		except Exception as e:
			self.message_post(body="Ocurrió un error al enviar archivos a ELAVON", subject="Registro no procesado")
			self.message_post(body="Exception: " + str(e.args[0]), subject="Registro no procesado")
			#self.status = 'error'
			self.env['cmp.message.log'].create({'log': str(e)})
	
	def send_files_to_elavon(self):
		ICPSudo = self.env['ir.config_parameter'].sudo()
		elavon_hostname = ICPSudo.get_param('itl_elavon_cron.elavon_hostname') or False
		elavon_port = ICPSudo.get_param('itl_elavon_cron.elavon_port') or False
		elavon_user = ICPSudo.get_param('itl_elavon_cron.elavon_user') or False
		elavon_password = ICPSudo.get_param('itl_elavon_cron.elavon_password') or False
		elavon_local_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_outbox_path') or False
		elavon_remote_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_inbox_path') or False
		try:
			client = paramiko.SSHClient()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			client.connect(hostname=elavon_hostname, port=elavon_port, username=elavon_user, password=elavon_password)
			ftp_client = client.open_sftp()
			ftp_client.chdir("/")
			if self.file_to_elavon:
				ftp_client.put(str(elavon_local_outbox_path) + "/" + str(self.filename_to_elavon), str(elavon_remote_inbox_path) + "/" + str(self.filename_to_elavon))
				self.status = 'sent'
				self.message_post(body="El archivo V/M se envió correctamente a ELAVON.", subject="Registro procesado")
			if self.file_amex_to_elavon:
				ftp_client.put(str(elavon_local_outbox_path) + "/" + str(self.filename_amex_to_elavon), str(elavon_remote_inbox_path) + "/" + str(self.filename_amex_to_elavon))
				self.status_amex = 'sent'
				self.message_post(body="El archivo Amex se envió correctamente a ELAVON.", subject="Registro procesado")
		except Exception as e:
			self.message_post(body="Exception: " + str(e.args[0]), subject="Registro no procesado")
			self.message_post(body="Ocurrió un error al enviar archivos a ELAVON", subject="Registro no procesado")
			#self.status = 'error'
			self.env['cmp.message.log'].create({'log': str(e)})

	def read_from_elavon(self):
		ICPSudo = self.env['ir.config_parameter'].sudo()
		elavon_hostname = ICPSudo.get_param('itl_elavon_cron.elavon_hostname') or False
		elavon_port = ICPSudo.get_param('itl_elavon_cron.elavon_port') or False
		elavon_user = ICPSudo.get_param('itl_elavon_cron.elavon_user') or False
		elavon_password = ICPSudo.get_param('itl_elavon_cron.elavon_password') or False
		elavon_local_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_inbox_path') or False
		elavon_remote_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_outbox_path') or False
		try:
			client = paramiko.SSHClient()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			client.connect(hostname=elavon_hostname, port=elavon_port, username=elavon_user, password=elavon_password)
			ftp_client = client.open_sftp()
			ftp_client.chdir("/")
		except Exception as e:
			self.message_post(body="Exception: " + str(e), subject="Registro no procesado")
			self.status = 'response_error'
			self.env['cmp.message.log'].create({'log': str(e)})
			return False, False, []

		filename = str(self.filename_to_elavon).split('.')[0]
		filename_error = False
		files_to_copy = []
		# Revisa si el archivo de error existe
		try:
			filename_error = filename + "ERROR.txt"
			remote_path = str(elavon_remote_outbox_path) + "/" + str(filename_error)
			ftp_client.stat(remote_path)
			files_to_copy.append(filename_error)
			_logger.info("------ SE ENCONTRÓ EL ARCHIVO DE ERROR ")
		except IOError:
			_logger.info("------ NO SE ENCONTRÓ EL ARCHIVO DE ERROR ")

		# Revisa si el archivo normal existe
		try:
			filename = filename + ".txt"
			remote_path = str(elavon_remote_outbox_path) + "/" + str(filename)
			ftp_client.stat(remote_path)
			normal_file_exists = True
			files_to_copy.append(filename)
			_logger.info("------ SE ENCONTRÓ EL ARCHIVO NORMAL ")
		except IOError:
			_logger.info("------ NO SE ENCONTRÓ EL ARCHIVO NORMAL ")

		files_correctly_copied = []
		for f_name in files_to_copy:
			try:
				remote_path = str(elavon_remote_outbox_path) + "/" + str(f_name)
				local_path = str(elavon_local_inbox_path) + "/" + str(f_name)
				_logger.info("--> remote_path: " + str(remote_path))
				_logger.info("--> local_path: " + str(local_path))
				ftp_client.get(remote_path, local_path)
				files_correctly_copied.append(f_name)
			except FileNotFoundError as e:
				_logger.info("------ NO SE ENCONTRÓ EL ARCHIVO : " + str(filename))
				self.env['cmp.message.log'].create({'log': str(e)})
				self.message_post(body="Advertencia: Error al leer archivo de respuesta", subject="Registro no procesado")
				self.message_post(body="Error: " + str(e.args[0]), subject="Registro no procesado")
				self.status = 'error'
		
		return files_correctly_copied

	def read_amex_from_elavon(self):
		ICPSudo = self.env['ir.config_parameter'].sudo()
		elavon_hostname = ICPSudo.get_param('itl_elavon_cron.elavon_hostname') or False
		elavon_port = ICPSudo.get_param('itl_elavon_cron.elavon_port') or False
		elavon_user = ICPSudo.get_param('itl_elavon_cron.elavon_user') or False
		elavon_password = ICPSudo.get_param('itl_elavon_cron.elavon_password') or False
		elavon_local_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_inbox_path') or False
		elavon_remote_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_outbox_path') or False
		try:
			client = paramiko.SSHClient()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			client.connect(hostname=elavon_hostname, port=elavon_port, username=elavon_user, password=elavon_password)
			ftp_client = client.open_sftp()
			ftp_client.chdir("/")
		except Exception as e:
			self.message_post(body="Exception: " + str(e), subject="Registro no procesado")
			self.status_amex = 'response_error'
			self.env['cmp.message.log'].create({'log': str(e)})
			return False, False, []

		filename = str(self.filename_amex_to_elavon).split('.')[0]
		filename_error = False
		files_to_copy = []
		# Revisa si el archivo de error existe
		try:
			filename_error = filename + "ERROR.txt"
			remote_path = str(elavon_remote_outbox_path) + "/" + str(filename_error)
			ftp_client.stat(remote_path)
			files_to_copy.append(filename_error)
			_logger.info("------ SE ENCONTRÓ EL ARCHIVO DE ERROR ")
		except IOError:
			_logger.info("------ NO SE ENCONTRÓ EL ARCHIVO DE ERROR ")

		# Revisa si el archivo normal existe
		try:
			filename = filename + ".txt"
			remote_path = str(elavon_remote_outbox_path) + "/" + str(filename)
			ftp_client.stat(remote_path)
			normal_file_exists = True
			files_to_copy.append(filename)
			_logger.info("------ SE ENCONTRÓ EL ARCHIVO NORMAL ")
		except IOError:
			_logger.info("------ NO SE ENCONTRÓ EL ARCHIVO NORMAL ")

		files_correctly_copied = []
		for f_name in files_to_copy:
			try:
				remote_path = str(elavon_remote_outbox_path) + "/" + str(f_name)
				local_path = str(elavon_local_inbox_path) + "/" + str(f_name)
				_logger.info("--> remote_path: " + str(remote_path))
				_logger.info("--> local_path: " + str(local_path))
				ftp_client.get(remote_path, local_path)
				files_correctly_copied.append(f_name)
			except FileNotFoundError as e:
				_logger.info("------ NO SE ENCONTRÓ EL ARCHIVO : " + str(filename))
				self.env['cmp.message.log'].create({'log': str(e)})
				self.message_post(body="Advertencia: Error al leer archivo de respuesta", subject="Registro no procesado")
				self.message_post(body="Error: " + str(e.args[0]), subject="Registro no procesado")
				self.status_amex = 'error'
		
		return files_correctly_copied
	
	def check_if_file_exists(self):
		ICPSudo = self.env['ir.config_parameter'].sudo()
		elavon_hostname = ICPSudo.get_param('itl_elavon_cron.elavon_hostname') or False
		elavon_port = ICPSudo.get_param('itl_elavon_cron.elavon_port') or False
		elavon_user = ICPSudo.get_param('itl_elavon_cron.elavon_user') or False
		elavon_password = ICPSudo.get_param('itl_elavon_cron.elavon_password') or False
		elavon_local_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_inbox_path') or False
		elavon_remote_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_outbox_path') or False

		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		client.connect(hostname=elavon_hostname, port=elavon_port, username=elavon_user, password=elavon_password)
		ftp_client = client.open_sftp()
		ftp_client.chdir("/" + str(elavon_remote_outbox_path))

	def process_elavon_response(self):
		cmp_files = self.env['cmp.message'].search([('status','=','sent')])
		_logger.info("--> Registros CMP a revisar en ELAVON: " + str(len(cmp_files)))
		if len(cmp_files) > 0:
			for cmp_message in cmp_files:
				_logger.info("--> Registro a revisar en ELAVON: " + str(cmp_message.filename_to_elavon))
				try:
					if not cmp_message.file_from_elavon:
						cmp_message.process_response()
					_logger.info("***> self.status: " + str(cmp_message.status))
					if cmp_message.status == 'partial' and (not cmp_message.status_amex or cmp_message.status_amex in ['done','partial']):
						cmp_message.send_rejection_file()
						cmp_message.status_file = 'sent_rejection'
						continue
					if cmp_message.status_amex == 'partial' and (not cmp_message.status or cmp_message.status in ['done','partial']):
						cmp_message.send_rejection_file()
						cmp_message.status_file = 'sent_rejection'
						continue
				except Exception as e:
					cmp_message.message_post(body="Error en al procesar archivo " + cmp_message.file_name + ": " + str(e.args[0]), subject="Registro no procesado")
					_logger.info("--> Error en al procesar archivo " + cmp_message.file_name + ": " + str(e.args[0]))
		else:
			_logger.info("--> No hay registros para procesar")
			cmp_log = self.env['cmp.message.log']
			cmp_log.create({'log': 'No hay archivos de CMP que procesar.'})

	def process_elavon_amex_response(self):
		cmp_files = self.env['cmp.message'].search([('status_amex','=','sent')])
		_logger.info("--> Registros CMP a revisar en ELAVON: " + str(len(cmp_files)))
		if len(cmp_files) > 0:
			for cmp_message in cmp_files:
				_logger.info("--> Registro a revisar en ELAVON: " + str(cmp_message.filename_amex_to_elavon))
				try:
					if not cmp_message.file_amex_from_elavon:
						cmp_message.process_amex_response()
					_logger.info("***> self.status_amex: " + str(cmp_message.status_amex))
					if cmp_message.status_amex == 'partial' and (not cmp_message.status or cmp_message.status in ['done','partial']):
						cmp_message.send_rejection_file()
						cmp_message.status_file = 'sent_rejection'
						continue
					if cmp_message.status == 'partial' and (not cmp_message.status_amex or cmp_message.status_amex in ['done','partial']):
						cmp_message.send_rejection_file()
						cmp_message.status_file = 'sent_rejection'
						continue
				except Exception as e:
					cmp_message.message_post(body="Error en al procesar archivo " + cmp_message.file_name + ": " + str(e.args[0]), subject="Registro no procesado")
					_logger.info("--> Error en al procesar archivo " + cmp_message.file_name + ": " + str(e.args[0]))
		else:
			_logger.info("--> No hay registros para procesar")
			cmp_log = self.env['cmp.message.log']
			cmp_log.create({'log': 'No hay archivos de CMP que procesar.'})

	def loop_files(self):
		if self.file_from_elavon:
			file_content = base64.decodestring(self.file_from_elavon)
			file_content = file_content.decode("utf-8")
			self.process_response_files(file_content, self.filename_from_elavon)
		if self.file_from_elavon_err:
			file_content = base64.decodestring(self.file_from_elavon_err)
			file_content = file_content.decode("utf-8")
			self.process_response_files(file_content, self.filename_from_elavon_err)
		if self.file_amex_from_elavon:
			file_content = base64.decodestring(self.file_amex_from_elavon)
			file_content = file_content.decode("utf-8")
			self.process_response_files_amex(file_content, self.filename_amex_from_elavon)
		if self.file_amex_from_elavon_err:
			file_content = base64.decodestring(self.file_amex_from_elavon_err)
			file_content = file_content.decode("utf-8")
			self.process_response_files_amex(file_content, self.filename_amex_from_elavon_err)

		if self.status == 'partial' or self.status_amex == 'partial':
			self.send_rejection_file()
		if self.status == 'done' and self.status_amex == 'done':
			self.status_file = 'done'


	def process_response_files(self, file_content, fname):

		file_lines = str(file_content).split('\n')
		message_errors = []
		rejections = []
		file_err = False
		has_rejections = False
		param = self.env['ir.config_parameter'].sudo()
		sr_company_id = param.get_param('itl_sr_interface.sr_company_id') or False

		if 'ERROR' in fname:
			file_err = True
		
		for line in file_lines:
			_logger.info("-> line: " + str(line))
			record = line.split('\t')
			reference = record[0]
			detail_id = int(reference.split('_')[0])
			invoice_id_str = reference.split('_')[1]
			if invoice_id_str != 'none':
				invoice_id = int(invoice_id_str)
				invoice_obj_id = self.env['account.invoice'].browse(invoice_id)
			if 'ERROR' in fname:
				response_code = record[-1]
			else:
				response_code = record[4]

			detail_obj_id = self.env['cmp.item'].browse(detail_id)
			if not detail_obj_id:
				message_errors.append("No se encontró el detalle con el ID: " + str(detail_id))
				self.status = 'error'
				continue
			if not invoice_obj_id and detail_obj_id.invoice_id:
				invoice_obj_id = detail_obj_id.invoice_id
			
			if not invoice_obj_id:
				message_errors.append("No se encontró la factura relacionada al detalle con ID " + str(detail_id))
				detail_obj_id.status = 'error'
				continue
			
			if response_code == '00':
				authorization_number = record[5]
				detail_obj_id.authorization_number = authorization_number
				detail_obj_id.response_code = '00'
				detail_obj_id.status = 'approved'
				try:
					invoice_obj_id.action_invoice_open()
					if invoice_obj_id.l10n_mx_edi_cfdi_uuid:
						# Create payment
						payment = self.with_context(force_company=sr_company_id).create_payment(invoice_obj_id)
						payment.post()
						# Send by email
						self.send_mail(invoice_obj_id)
				except Exception as e:
					message_errors.append("Error al procesar factura: " + str(e.args[0]))
					self.status = 'error'
					continue
			else:
				has_rejections = True
				if response_code not in response_codes:
					detail_obj_id.other_response_code = response_code
				else:
					detail_obj_id.response_code = response_code
				detail_obj_id.status = 'rejected'

				#rejections.append({'line': record, 'detail_id': detail_id, 'invoice_id': invoice_id})
		if has_rejections or file_err:
			self.status = 'partial'
			#self.send_rejection_file()
		else:
			self.status = 'done'

	def process_response_files_amex(self, file_content, fname):

		file_lines = str(file_content).split('\n')
		message_errors = []
		rejections = []
		file_err = False
		has_rejections = False
		param = self.env['ir.config_parameter'].sudo()
		sr_company_id = param.get_param('itl_sr_interface.sr_company_id') or False

		if 'ERROR' in fname:
			file_err = True
		
		for line in file_lines:
			_logger.info("-> line: " + str(line))
			record = line.split('\t')
			reference = record[0]
			detail_id = int(reference.split('_')[0])
			invoice_id_str = reference.split('_')[1]
			if invoice_id_str != 'none':
				invoice_id = int(invoice_id_str)
				invoice_obj_id = self.env['account.invoice'].browse(invoice_id)
			if 'ERROR' in fname:
				response_code = record[-1]
			else:
				response_code = record[4]

			detail_obj_id = self.env['cmp.item'].browse(detail_id)
			if not detail_obj_id:
				message_errors.append("No se encontró el detalle con el ID: " + str(detail_id))
				self.status_amex = 'error'
				continue
			if not invoice_obj_id and detail_obj_id.invoice_id:
				invoice_obj_id = detail_obj_id.invoice_id

			if not invoice_obj_id:
				message_errors.append("No se encontró la factura relacionada al detalle con ID " + str(detail_id))
				detail_obj_id.status = 'error'
				continue
			
			if response_code == '00':
				authorization_number = record[5]
				detail_obj_id.authorization_number = authorization_number
				detail_obj_id.response_code = '00'
				detail_obj_id.status = 'approved'
				try:
					invoice_obj_id.action_invoice_open()
					if invoice_obj_id.l10n_mx_edi_cfdi_uuid:
						# Create payment
						payment = self.with_context(force_company=sr_company_id).create_payment(invoice_obj_id)
						payment.post()
						# Send by email
						self.send_mail(invoice_obj_id)
				except Exception as e:
					message_errors.append("Error al procesar factura: " + str(e.args[0]))
					self.status_amex = 'error'
					continue
			else:
				has_rejections = True
				if response_code not in response_codes:
					detail_obj_id.other_response_code = response_code
				else:
					detail_obj_id.response_code = response_code
				detail_obj_id.status = 'rejected'

				#rejections.append({'line': record, 'detail_id': detail_id, 'invoice_id': invoice_id})
		if has_rejections or file_err:
			self.status_amex = 'partial'
			#self.send_rejection_file()
		else:
			self.status_amex = 'done'

	def process_response(self):
		if self.file_from_elavon:
			self.message_post(body="Advertencia: El archivo de respuesta de ELAVON ya fue procesado", subject="Registro no procesado")
			return
		files_correctly_copied = self.read_from_elavon()

		if len(files_correctly_copied) == 0:
			return

		param = self.env['ir.config_parameter'].sudo()
		sr_company_id = param.get_param('itl_sr_interface.sr_company_id') or False
		elavon_local_inbox_path = param.get_param('itl_elavon_cron.elavon_local_inbox_path') or False

		file_err = False
		has_rejections = False
		for fname in files_correctly_copied:
			try:
				if os.stat(elavon_local_inbox_path + '/' + str(fname)).st_size == 0:
					continue

				file_content_binary = open(elavon_local_inbox_path + '/' + str(fname), 'rb')
				file_content_normal = open(elavon_local_inbox_path + '/' + str(fname), 'r')
			except Exception as e:
				self.message_post(body="Advertencia: Error al leer archivo de respuesta", subject="Registro no procesado")
				self.message_post(body="Error: " + str(e.args[0]), subject="Registro no procesado")
				self.status = 'error'
				return

			file_content_b = file_content_binary.read()
			_logger.info("-> type file_content_b: " + str(file_content_b.decode()))
			file_content = file_content_normal.read()
			_logger.info("-> file_content: " + str(file_content))
			file_b64 = base64.b64encode(file_content_b)

			if 'ERROR' not in fname:
				self.file_from_elavon = file_b64
				self.filename_from_elavon = fname
			else:
				self.file_from_elavon_err = file_b64
				self.filename_from_elavon_err = fname
				file_err = True

			file_lines = str(file_content).split('\n')
			message_errors = []
			rejections = []
			
			for line in file_lines:
				invoice_obj_id = False
				_logger.info("-> line: " + str(line))
				record = line.split('\t')
				reference = record[0]
				detail_id = int(reference.split('_')[0])
				invoice_id_str = reference.split('_')[1]
				if invoice_id_str != 'none':
					invoice_id = int(invoice_id_str)
					invoice_obj_id = self.env['account.invoice'].browse(invoice_id)
				if 'ERROR' in fname:
					response_code = record[-1]
				else:
					response_code = record[4]

				detail_obj_id = self.env['cmp.item'].browse(detail_id)
				if not detail_obj_id:
					message_errors.append("No se encontró el detalle con el ID: " + str(detail_id))
					self.status = 'error'
					continue
				if not invoice_obj_id and detail_obj_id.invoice_id:
					invoice_obj_id = detail_obj_id.invoice_id
				if not invoice_obj_id:
					message_errors.append("No se encontró la factura relacionada al detalle con ID " + str(detail_id))
					detail_obj_id.status = 'error'
					#continue
				
				if response_code == '00':
					authorization_number = record[5]
					detail_obj_id.authorization_number = authorization_number
					detail_obj_id.response_code = '00'
					detail_obj_id.status = 'approved'
					if invoice_obj_id:
						try:
							invoice_obj_id.action_invoice_open()
							if invoice_obj_id.l10n_mx_edi_cfdi_uuid:
								# Create payment
								payment = self.with_context(force_company=sr_company_id).create_payment(invoice_obj_id)
								payment.post()
								# Send by email
								self.send_mail(invoice_obj_id)
						except Exception as e:
							message_errors.append("Error al procesar factura: " + str(e.args[0]))
							self.status = 'error'
							#continue
				else:
					has_rejections = True
					if response_code not in response_codes:
						detail_obj_id.other_response_code = response_code
					else:
						detail_obj_id.response_code = response_code
					detail_obj_id.status = 'rejected'

					#rejections.append({'line': record, 'detail_id': detail_id, 'invoice_id': invoice_id})
		if has_rejections or file_err:
			self.status = 'partial'
			#self.send_rejection_file()
		else:
			self.status = 'done'
		self.message_post(body="El archivo de respuesta V/M se procesó correctamente", subject="Registro procesado")

	def process_amex_response(self):
		if self.file_amex_from_elavon:
			self.message_post(body="Advertencia: El archivo de respuesta de ELAVON ya fue procesado", subject="Registro no procesado")
			return
		files_correctly_copied = self.read_amex_from_elavon()

		if len(files_correctly_copied) == 0:
			return

		param = self.env['ir.config_parameter'].sudo()
		sr_company_id = param.get_param('itl_sr_interface.sr_company_id') or False
		elavon_local_inbox_path = param.get_param('itl_elavon_cron.elavon_local_inbox_path') or False

		file_err = False
		has_rejections = False
		for fname in files_correctly_copied:
			try:
				if os.stat(elavon_local_inbox_path + '/' + str(fname)).st_size == 0:
					continue

				file_content_binary = open(elavon_local_inbox_path + '/' + str(fname), 'rb')
				file_content_normal = open(elavon_local_inbox_path + '/' + str(fname), 'r')
			except Exception as e:
				self.message_post(body="Advertencia: Error al leer archivo de respuesta", subject="Registro no procesado")
				self.message_post(body="Error: " + str(e.args[0]), subject="Registro no procesado")
				self.status_amex = 'error'
				return

			file_content_b = file_content_binary.read()
			_logger.info("-> type file_content_b: " + str(file_content_b.decode()))
			file_content = file_content_normal.read()
			_logger.info("-> file_content: " + str(file_content))
			file_b64 = base64.b64encode(file_content_b)

			if 'ERROR' not in fname:
				self.file_amex_from_elavon = file_b64
				self.filename_amex_from_elavon = fname
			else:
				self.file_amex_from_elavon_err = file_b64
				self.filename_amex_from_elavon_err = fname
				file_err = True

			file_lines = str(file_content).split('\n')
			message_errors = []
			rejections = []
			
			for line in file_lines:
				invoice_obj_id = False
				_logger.info("-> line: " + str(line))
				record = line.split('\t')
				reference = record[0]
				detail_id = int(reference.split('_')[0])
				invoice_id_str = reference.split('_')[1]
				if invoice_id_str != 'none':
					invoice_id = int(invoice_id_str)
					invoice_obj_id = self.env['account.invoice'].browse(invoice_id)
				if 'ERROR' in fname:
					response_code = record[-1]
				else:
					response_code = record[4]

				detail_obj_id = self.env['cmp.item'].browse(detail_id)
				if not detail_obj_id:
					message_errors.append("No se encontró el detalle con el ID: " + str(detail_id))
					self.status_amex = 'error'
					continue
				if not invoice_obj_id and detail_obj_id.invoice_id:
					invoice_obj_id = detail_obj_id.invoice_id
				if not invoice_obj_id:
					message_errors.append("No se encontró la factura relacionada al detalle con ID " + str(detail_id))
					detail_obj_id.status = 'error'
					#continue
				
				if response_code == '00':
					authorization_number = record[5]
					detail_obj_id.authorization_number = authorization_number
					detail_obj_id.response_code = '00'
					detail_obj_id.status = 'approved'
					if invoice_obj_id:
						try:
							invoice_obj_id.action_invoice_open()
							if invoice_obj_id.l10n_mx_edi_cfdi_uuid:
								# Create payment
								payment = self.with_context(force_company=sr_company_id).create_payment(invoice_obj_id)
								payment.post()
								# Send by email
								self.send_mail(invoice_obj_id)
						except Exception as e:
							message_errors.append("Error al procesar factura: " + str(e.args[0]))
							self.status_amex = 'error'
							#continue
				else:
					has_rejections = True
					if response_code not in response_codes:
						detail_obj_id.other_response_code = response_code
					else:
						detail_obj_id.response_code = response_code
					detail_obj_id.status = 'rejected'

					#rejections.append({'line': record, 'detail_id': detail_id, 'invoice_id': invoice_id})
		if has_rejections or file_err:
			self.status_amex = 'partial'
			#self.send_rejection_file()
		else:
			self.status_amex = 'done'
		self.message_post(body="El archivo de respuesta Amex se procesó correctamente", subject="Registro procesado")

	def send_mail(self, invoice):
		template_id = self.env.ref('account.email_template_edi_invoice', False)
		if template_id:
			self.env['mail.template'].browse(template_id.id).send_mail(invoice.id, force_send=True)

	def send_rejection_to_cmp(self):
		pass
		
	
	def send_rejection_file(self):
		rejection_file = self.validate_rejection_file()
		self.create_rejection_file(rejection_file)

	def create_rejection_file(self, rejection_file):
		
		param = self.env['ir.config_parameter'].sudo()
		sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
		company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
		cmp_odoo_recurringprepaymentsextract_outbound_path = company_id.cmp_odoo_recurringprepaymentsextract_outbound_path
		rejection_file_name = str(self.file_name).split('.')[0] + ".in"
		with open(str(cmp_odoo_recurringprepaymentsextract_outbound_path) + "/" + str(rejection_file_name), 'w', encoding='utf-8') as file:
			json.dump(rejection_file, file, indent=4, ensure_ascii=False)
		file_content_binary = open(str(cmp_odoo_recurringprepaymentsextract_outbound_path) + "/" + str(rejection_file_name), 'rb')
		file_content = file_content_binary.read()
		file_b64 = base64.b64encode(file_content)
		self.file_rejection_to_cmp = file_b64
		self.filename_file_rejection_to_cmp = rejection_file_name
		try:
			success_connection, error = company_id.check_credentials()
			client = paramiko.SSHClient()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			_logger.info("----> before connect...")
			client.connect(hostname=company_id.cmp_host, port=company_id.cmp_port, username=company_id.cmp_user, password=company_id.cmp_password, look_for_keys=False)
			_logger.info("----> after connect...")
			ftp_client = client.open_sftp()

			ftp_client.put(str(cmp_odoo_recurringprepaymentsextract_outbound_path) + "/" + str(rejection_file_name), company_id.cmp_recurringprepaymentsextract_inbound_path + "/" + str(rejection_file_name))
			self.status_file = 'sent_rejection'
			self.message_post(body="El archivo de rejections se generó y envió correctamente a CMP", subject="Registro procesado")
		except Exception as e:
			self.message_post(body="Advertencia: Error al enviar archivo a CMP: Error: " + str(e), subject="Registro no procesado")
			self.status_file = 'error'
			return

		return

	def validate_rejection_file(self):
		detail_ids = self.cmp_item_ids.filtered(lambda r: r.status == 'rejected')
		_logger.info("---> VALIDATING REJECTION JSON ------")
		date_tz = pytz.UTC.localize(datetime.strptime(str(fields.Datetime.now()), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(timezone('America/Mexico_City'))
		json_datetime = date_tz.strftime("%Y-%m-%dT%H:%M:%S.000-0500")
		_logger.info("---> json_datetime: " + str(json_datetime))
		rejection_file_name = str(self.file_name).split('.')[0] + ".in"
		rejection_file = {
			"interfaceCategory": "Payments",
			"interfaceType": "Card Pre Payments",
			"version": 1.0,
			"externalFileName": rejection_file_name,
			"transformDateTime": json_datetime,
			"transmitDateTime": json_datetime
		}
		details = []
		i = 1
		for rej in detail_ids:
			detail = {}
			#detail_obj_id = self.env['cmp.item'].browse(rej['detail_id'])
			detail['detailSequence'] = i
			detail['accountNumber'] = int(rej.account_number)
			detail['transactionNumber'] = int(rej.transaction_number)
			detail['externalReference'] = str(rej.id) + '_' + str(rej.invoice_id.id if rej.invoice_id else '')
			detail['transactionDetail'] = ''
			if rej.response_code:
				detail['transactionSummary'] = dict(rej._fields['response_code'].selection).get(rej.response_code)
				detail['transactionCode'] = rej.response_code
			else:
				detail['transactionSummary'] = rej.other_response_code
				detail['transactionCode'] = rej.other_response_code
				detail['transactionDetail'] = "El número de token no es válido o no sólo contiene números"
			details.append(detail)

		rejection_file.update(recurringPrePaymentsCardRejectionsDetail=details)
		file_content_binary = open(recurring_payment_rejection_schema_path, 'r')
		json_schema = file_content_binary.read()
		json_schema = json.loads(json_schema)
		#rejection_file = json.dumps(rejection_file)
		try:
			validate(instance=rejection_file, schema=json_schema)
		except jsonschema.exceptions.ValidationError as err:
			self.message_post(body="Advertencia: El archivo JSON generado no es valido. Error: " + str(err) + " | " + str(err.absolute_path) + " | " + str(err.absolute_schema_path), subject="Registro no procesado")
			return
		
		_logger.info("--> VALID JSON ----")

		return rejection_file

	def create_payment(self, invoice):
		"""
		Crea pago para la factura indicada
		"""
		AccountRegisterPayments = self.env['account.register.payments']

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

		AccountPayment = self.env['account.payment']
		return AccountPayment.create(payment_vals)


	def process_content(self):
		if self.content_file:
			content_file = str(self.content_file).replace("\'", "\"")
			file_content_json = json.loads(content_file)
			details = file_content_json['details']

			for m in self.cmp_item_ids:
				m.unlink()

			for detail in details:
				cmp_item = self.env['cmp.item']
				item_vals = {}

				accountNumber = detail['accountNumber']
				sale_subscription_id = self.env['sale.subscription'].search([('account_id_ref','=',accountNumber)])

				if sale_subscription_id:
					invoice_values = sale_subscription_id._prepare_invoice()
					for inv_line in invoice_values['invoice_line_ids']:
						price = float(detail['amount'])
						untaxed_price = price / 1.16
						inv_line[2]['price_unit'] = untaxed_price
						_logger.info("---<> inv_line: " + str(inv_line))
					#new_invoice = self.env['account.invoice'].with_context(context_company).create(invoice_values)
					_logger.info("----> invoice_values: " + str(invoice_values))
					raise ValidationError(_("Testing..."))

				item_vals.update(
					transaction_number = detail['transactionNumber'],
					payment_type = detail['paymentType'],
					account_number = detail['accountNumber'],
					amount = detail['amount'],
					name_on_card = detail['nameOnCard'],
					card_number = detail['cardNumber'],
					start_date = detail['startDateYymm'],
					end_date = detail['endDateYymm'],
					card_reference_number = detail['cardReferenceNumber'],
					card_type = detail['cardType'],
					cmp_message_id = self.id
					)

				cmp_item.create(item_vals)

class CmpItem(models.Model):
	_name = "cmp.item"
	_inherit = ['mail.thread']
	_description = "CMP Item"
	_rec_name = "transaction_number"

	def _get_default_company(self):
		param = self.env['ir.config_parameter'].sudo()
		sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
		company_id = False
		if sr_company_id:
			company_id = self.env['res.company'].browse(int(sr_company_id))
		
		return company_id


	status = fields.Selection([('new','New'),('sent','Sent'),('approved','Approved'),('rejected','Rejected'),('error','Error')], default='new', copy=False)
	transaction_number = fields.Char(string="transactionNumber", readonly=True, store=True, copy=False)
	payment_type = fields.Char(string="paymentType", readonly=True, store=True, copy=False)
	account_number = fields.Char(string="accountNumber", readonly=True, store=True, copy=False)
	amount = fields.Float(string="amount", readonly=True, store=True, copy=False)
	name_on_card = fields.Char(string="nameOnCard", readonly=True, store=True, copy=False)
	card_number = fields.Char(string="cardNumber", readonly=True, store=True, copy=False)
	start_date = fields.Char(string="startDateYymm", readonly=True, store=True, copy=False)
	end_date = fields.Char(string="endDateYymm", readonly=True, store=True, copy=False)
	card_reference_number = fields.Char(string="cardReferenceNumber", readonly=True, store=True, copy=False)
	card_type = fields.Char(string="cardType", readonly=True, store=True, copy=False)
	response_code = fields.Selection([('00', 'Cargo exitoso'),
										('01', 'Llamar al banco emisor'),
										('02', 'Llamar al banco emisor'),
										('04', 'Recoger tarjeta'),
										('05', 'Rechazar'),
										('06', 'Inhabilitado para procesar'),
										('07', 'Recoger tarjeta'),
										('12', 'Rechazar'),
										('13', 'Importe invalido'),
										('14', 'Tarjeta invalida'),
										('36', 'Tarjeta restringida'),
										('41', 'Tarjeta reportado como extraviada'),
										('43', 'Tarjeta reportada como robada'),
										('51', 'Fondos insuficientes'),
										('57', 'Transacción no permitida'),
										('62', 'Tarjeta restringida'),
										('78', 'Código reservado'),
										('84', 'Cargo reservado'),
										('100', 'Rechazo (AMEX)'),
										('101', 'Tarjeta expirada (AMEX)'),
										('107', 'Llamar al banco emisor (AMEX)'),
										('200', 'Rechazo Recoger tarjeta'),
										('T5', 'Rechazo Recoger tarjeta'),

										('15', 'No existe el emisor'),
										('45', 'Código reservado'),
										('46', 'Código reservado'),
										('48', 'Código reservado'),
										('80', 'Rechazar'),
										('82', 'Tarjeta inválida'),
										('83', 'Tarjeta inválida'),
										('87', 'Tarjeta inválida'),
										('94', 'Transacción duplicada'),
										('N0', 'Reintente'),
										('R1', 'Reintente'),

										('03', 'Comercio inválido'),
										('30', 'Error de formato'),
										('52', 'Cuenta incorrecta'),
										('61', 'Límite excedido'),
										('65', 'Límite excedido'),
										('N8', 'Rechazar'),
										('O8', 'Tarjeta inválida'),
										('P1', 'Transacción no permitida'),
										('T4', 'Rechazar'),

										('34', 'Sospecha de fraude'),
										('35', 'Recoger tarjeta, contactar al adquirente'),
										('37', 'Contactar al adquirente'),
										('56', 'No hay registro de tarjeta'),
										('Q5', 'Tarjeta robada, contacte al adquirente'),

										('N7', 'TH no acepta ningún cargo recurrente de este comercio'),
										('N6', 'TH no acepta el cargo recurrente del contrato indicado'),
										('otro', 'Otro')], string="Response code", readonly=False, store=True, copy=False)
	other_response_code = fields.Char(string="Other response code", readonly=True, store=True, copy=False)
	authorization_number = fields.Char(string="Authorization code", readonly=True, store=True, copy=False)
	token_type = fields.Selection([('visa_mastercard','Visa/MasterCard'),('amex','Amex')], string="Token type", readonly=True, store=True, copy=False)
	company_id = fields.Many2one('res.company', string="Compañía", readonly=True, store=True, default=_get_default_company)
										

	invoice_id = fields.Many2one('account.invoice', string="Related Invoice", readonly=True, store=True, copy=False)
	cmp_message_id = fields.Many2one('cmp.message', readonly=True, store=True, copy=False, ondelete='cascade')

	def process_document(self):
		pass

	def generate_invoice(self):
		if self.invoice_id:
			raise ValidationError("La factura ya fue generada.")
		sale_subscription_id = self.env['sale.subscription'].with_context(force_company=self.company_id.id).search([('account_id_ref','=',self.account_number),('company_id.id','=',self.company_id.id)], limit=1)
		_logger.info("-> sale_subscription_id: " + str(sale_subscription_id))
		if not sale_subscription_id:
			raise ValidationError("No se encontró la suscripción asociada al account number " + str(self.account_number) + ".")
		if self.amount == 0.0:
			raise ValidationError("El campo amount es 0.")
		product_plan = sale_subscription_id.recurring_invoice_line_ids.filtered(lambda line: line.product_id.isRecurring or 'Recurrente' in line.product_id.name)
		if len(product_plan) == 0:
			raise ValidationError("La suscripción asociada al account number " + str(self.account_number) + " no tiene un producto de tipo Plan recurrente.")
		if len(product_plan) > 1:
			raise ValidationError("La suscripción asociada al account number " + str(self.account_number) + " tiene más de un producto de tipo Plan recurrente.")
		total_amount = float(self.amount)
		total_untaxed_amount = float(total_amount) / 1.16
		try:
			invoice_id = sale_subscription_id.with_context({'price_unit': total_untaxed_amount})._recurring_create_invoice()
			self.invoice_id = invoice_id
		except Exception as e:
			_logger.info("--> Exception: " + str(e))
			raise ValidationError("Ocurrió una excepción: " + str(e))

class CmpReceiptPrintExtract(models.Model):
	_name = "cmp.receipt.print.extract"
	_inherit = ['mail.thread']
	_description = "CMP Receipt print extract"
	_rec_name = "id"

	name = fields.Char("Type")
	content_file = fields.Text("Content")
	status = fields.Selection([('new','New'),('done','Successfully processed'),('error','Processed without success')], default='new', copy=False)
	file = fields.Binary(string="CMP file")
	file_name = fields.Char('File Name')

class CmpDatawarehouseExtract(models.Model):
	_name = "cmp.datawarehouse.extract"
	_inherit = ['mail.thread']
	_description = "CMP Datawarehouse extract"
	_rec_name = "id"

	name = fields.Char("Type")
	content_file = fields.Text("Content")
	status = fields.Selection([('new','New'),('done','Successfully processed'),('error','Processed without success')], default='new', copy=False)
	file = fields.Binary(string="CMP file")
	file_name = fields.Char('File Name')