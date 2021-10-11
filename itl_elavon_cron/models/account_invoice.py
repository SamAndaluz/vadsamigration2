# -*- coding: utf-8 -*-

from odoo import models, fields, api
import paramiko
from pathlib import Path
from datetime import datetime


class AccountInvoiceCustom(models.Model):
    _inherit = 'account.invoice'


    @api.model
    def check_open_invoices(self):
        """
        This method check all open invoices and make a txt file with
        invoice and customer info to drop it in sftp.mitec.com.mx Inbox
        """
        ICPSudo = self.env['ir.config_parameter'].sudo()
        elavon_hostname = ICPSudo.get_param('itl_elavon_cron.elavon_hostname') or False
        elavon_port = ICPSudo.get_param('itl_elavon_cron.elavon_port') or False
        elavon_user = ICPSudo.get_param('itl_elavon_cron.elavon_user') or False
        elavon_password = ICPSudo.get_param('itl_elavon_cron.elavon_password') or False
        elavon_id_buzon = ICPSudo.get_param('itl_elavon_cron.elavon_id_buzon') or False
        elavon_id_company = ICPSudo.get_param('itl_elavon_cron.elavon_id_company') or False
        #elavon_local_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_inbox_path') or False
        elavon_local_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_outbox_path') or False
        elavon_remote_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_inbox_path') or False
        #elavon_remote_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_outbox_path') or False

        datetime_object = datetime.now()
        #path = Path(__file__).parent.absolute()

        filename = "pcv" + str(elavon_id_company) + str(elavon_id_buzon) + str(datetime_object.year)[-2:] + str('{:02d}'.format(datetime_object.month)) + str('{:02d}'.format(datetime_object.day)) + str('{:02d}'.format(datetime_object.hour)) + str('{:02d}'.format(datetime_object.minute)) + str("_token.txt")

        open_invoices = self.env['account.invoice'].search([('state','=','open')])
        invoice = False
        if open_invoices:
            invoice = open_invoices[0]

        #with open(str(elavon_local_outbox_path) + "/" + str(filename), 'w') as file:
        #    for invoice in open_invoices:
        #        email = invoice.partner_id.email
        #        if not email:
        #            email = ""
        #        file.write(str(invoice.partner_id.id) + "_" + invoice.number + '\t' + str("9487622619740347") + '\t' + str(invoice.amount_total) + '\t' + str(email) + '\t' + str("WDSER45C64D1") + '\n')
        with open(str(elavon_local_outbox_path) + "/" + str(filename), 'w') as file:
            #if invoice:
            #    file.write(str(invoice.partner_id.id) + "_" + str(invoice.number).replace('/','_') + '\t' + str("9487622619740347") + '\t' + str(invoice.amount_total) + '\t' + str(email) + '\t' + str("WDSER45C64D1") + '\n')
            #else:

            #removing CONTRATO
            file.write("15_A_2020_0011" + '\t' + str("6636108393579370") + '\t' + str("1.75") + '\t' + str("markesz2181@gmail.com") + '\t' + str("WDSER45C64D1"))

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=elavon_hostname, port=elavon_port, username=elavon_user, password=elavon_password)
        ftp_client = client.open_sftp()
        ftp_client.chdir("/")
        
        ftp_client.put(str(elavon_local_outbox_path) + "/" + str(filename), str(elavon_remote_inbox_path) + "/" + str(filename))


    @api.model
    def check_server_outbox(self):
        """
        This method looking for files in remote server Outbox.
        """
        ICPSudo = self.env['ir.config_parameter'].sudo()
        elavon_hostname = ICPSudo.get_param('itl_elavon_cron.elavon_hostname') or False
        elavon_port = ICPSudo.get_param('itl_elavon_cron.elavon_port') or False
        elavon_user = ICPSudo.get_param('itl_elavon_cron.elavon_user') or False
        elavon_password = ICPSudo.get_param('itl_elavon_cron.elavon_password') or False
        elavon_id_buzon = ICPSudo.get_param('itl_elavon_cron.elavon_id_buzon') or False
        elavon_id_company = ICPSudo.get_param('itl_elavon_cron.elavon_id_company') or False
        elavon_local_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_inbox_path') or False
        #elavon_local_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_outbox_path') or False
        #elavon_remote_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_inbox_path') or False
        elavon_remote_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_outbox_path') or False

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=elavon_hostname, port=elavon_port, username=elavon_user, password=elavon_password)
        ftp_client = client.open_sftp()
        ftp_client.chdir(str(elavon_remote_outbox_path))

        for i in ftp_client.listdir():
            lstatout=str(ftp_client.lstat(i)).split()[0]
            if 'd' not in lstatout:
                ftp_client.get(str(i), elavon_local_inbox_path + "/" + str(i))
        