from odoo import api, fields, models, _
import paramiko
import os
import json
from datetime import date
import base64
import subprocess
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class CmpGetFile(models.TransientModel):
    _name = "cmp.get.file"
    _description = "Get file from CMP"

    def get_recurring_files_action(self):
        try:
            param = self.env['ir.config_parameter'].sudo()
            sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
            company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
            success_connection, error = company_id.check_credentials()
        except Exception as e:
            cmp_log = self.env['cmp.message.log'].create({'log': str(e)})
            return
        if success_connection:
            remote_path = company_id.cmp_recurringprepaymentsextract_path
            local_path = company_id.cmp_recurringprepaymentsextract_local_path
            file_type = 'recurring'
            self.get_recurring_files(company_id, remote_path, local_path, file_type)

    def get_recurring_encripted_files_action(self):
        try:
            param = self.env['ir.config_parameter'].sudo()
            sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
            company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
            success_connection, error = company_id.check_credentials()
            if success_connection:
                remote_path = company_id.cmp_recurringprepaymentsextract_path
                local_path = company_id.cmp_recurringprepaymentsextract_local_path
                file_type = 'recurring'
                self.decrypt_file(company_id, remote_path, local_path, file_type)
        except Exception as e:
            cmp_log = self.env['cmp.message.log'].create({'log': str(e)})

    def do_action(self):
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        success_connection, error = company_id.check_credentials()
        if success_connection:
            ctx = dict(self._context)
            _logger.info("---> success_connection...")
            remote_path = False
            local_path = False
            file_type = False
            if ctx.get('recurring'):
                remote_path = company_id.cmp_recurringprepaymentsextract_path
                local_path = company_id.cmp_recurringprepaymentsextract_local_path
                file_type = 'recurring'
            if ctx.get('receipt'):
                remote_path = company_id.cmp_receiptprintextract_path
                local_path = company_id.cmp_receiptprintextract_local_path
                file_type = 'receipt'
            if ctx.get('datawarehouse'):
                remote_path = company_id.cmp_datawarehouse_extracts_path
                local_path = company_id.cmp_datawarehouse_extracts_local_path
                file_type = 'datawarehouse'
            try:
                self.decrypt_file(company_id, remote_path, local_path, file_type)
                _logger.info("---> success decrypt_file...")
            except Exception as e:
                cmp_log = self.env['cmp.message.log'].create({'log': str(e)})
                _logger.info("Connection error: " + str(e))
        else:
            _logger.info("---> success_connection false: " + str(error))
            cmp_log = self.env['cmp.message.log'].create({'log': str(error)})

    def do_action_rename(self):
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        success_connection, error = company_id.check_credentials()
        if success_connection:
            ctx = dict(self._context)
            _logger.info("---> success_connection...")
            remote_path = False
            local_path = False
            file_type = False
            if ctx.get('recurring'):
                remote_path = company_id.cmp_recurringprepaymentsextract_path
                local_path = company_id.cmp_recurringprepaymentsextract_local_path
                file_type = 'recurring'
            if ctx.get('receipt'):
                remote_path = company_id.cmp_receiptprintextract_path
                local_path = company_id.cmp_receiptprintextract_local_path
                file_type = 'receipt'
            if ctx.get('datawarehouse'):
                remote_path = company_id.cmp_datawarehouse_extracts_path
                local_path = company_id.cmp_datawarehouse_extracts_local_path
                file_type = 'datawarehouse'
            try:
                self.reset_file(company_id, remote_path)
                _logger.info("---> success decrypt_file...")
            except Exception as e:
                cmp_log = self.env['cmp.message.log'].create({'log': str(e)})
                _logger.info("Connection error: " + str(e))
        else:
            _logger.info("---> success_connection false: " + str(error))
            cmp_log = self.env['cmp.message.log'].create({'log': str(error)})

    def get_recurring_files(self, company_id, remote_path, local_path, o_type):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            _logger.info("----> before connect...")
            client.connect(hostname=company_id.cmp_host, port=company_id.cmp_port, username=company_id.cmp_user, password=company_id.cmp_password, look_for_keys=False)
            _logger.info("----> after connect...")
            ftp_client = client.open_sftp()
            directories = ftp_client.chdir(remote_path)
            list_files = ftp_client.listdir()
        except Exception as e:
            cmp_log = self.env['cmp.message.log'].create({'log': str(e)})
            _logger.info("Connection error: " + str(e))
            return
        _logger.info("--> list_files: " + str(list_files))
        #new_files = filter(lambda x: 'DONE_ODOO' not in x or 'done' not in x, list_files)
        for l in list_files:
            _logger.info("---> file: " + str(l))
            if not ('done' in l or 'DONE_ODOO_' in l):
                _logger.info("---> file_new: " + str(l))
        new_files = [x for x in list_files if not ('done' in x or 'DONE_ODOO_' in x)]
        #new_files = list(new_files)
        _logger.info("----> new files: " + str(new_files))
        json_files = []
        cmp_log = self.env['cmp.message.log']
        message_log = ''
        if new_files:
            error_messages = []
            error_message1 = False
            for i in new_files:
                try:
                    lstatout = str(ftp_client.lstat(i)).split()[0]
                    _logger.info("----> lstatout: " + str(lstatout))
                    if 'd' not in lstatout:
                        f_name = i
                        _logger.info("----> " + str(f_name) + " is a file")
                        if not ('done' in f_name or 'DONE_ODOO_' in f_name):
                            _logger.info("----> " + str(f_name) + " doesn't have DONE_ODOO_")
                            json_files.append(f_name)
                            ftp_client.get(str(f_name), local_path + "/" + str(f_name))
                except Exception as e:
                    #cmp_log = self.env['cmp.message.log'].create({'log': str(e)})
                    error_messages.append("Error: " + str(e) + "                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            . File: " + str(f_name))
                    _logger.info("Error log: " + str(e))
                    continue
            if len(error_messages) > 0:
                error_message1 = "\n".join(error_messages)
                        

            base_path = os.path.dirname(local_path)
            files = [f for f in os.listdir(base_path)]
            decrypt_file = None
            decripted_files = []
            error_message2 = False
            final_error_message = False
            if len(files) > 0:
                errors = []
                for file in json_files:
                    file_content_binary = open(local_path + '/' + str(file), 'rb')
                    _logger.info("---> Processing file: " + str(file))
                    error_message = self.process_file(file_content_binary, o_type)
                    if error_message:
                        #cmp_log = self.env['cmp.message.log'].create({'log': str(e)})
                        errors.append("Error: " + str(error_message) + ". File: " + str(file))
                    os.unlink(local_path + '/' + str(file))
                    renamed_file = "DONE_ODOO_" + file
                    old_path = remote_path + '/' + file
                    new_path = remote_path + '/' + renamed_file
                    ftp_client.rename(old_path, new_path)
                if len(errors) > 0:
                    error_message2 = "\n".join(errors)
                    final_error_message = error_message2
                    if error_message1:
                        final_error_message = error_message2 + '\n' + error_message2
            if final_error_message:
                cmp_log = self.env['cmp.message.log'].create({'log': final_error_message})
        else:
            cmp_log.create({'log': 'No hay archivos nuevos en el directorio: ' + str(remote_path)})


    def decrypt_file(self, company_id, remote_path, local_path, o_type):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        _logger.info("----> before connect...")
        client.connect(hostname=company_id.cmp_host, port=company_id.cmp_port, username=company_id.cmp_user, password=company_id.cmp_password, look_for_keys=False)
        _logger.info("----> after connect...")
        ftp_client = client.open_sftp()
        directories = ftp_client.chdir(remote_path)
        list_files = ftp_client.listdir()
        _logger.info("--> list_files: " + str(list_files))
        new_files = filter(lambda x: 'DONE_ODOO' not in x, list_files)
        new_files = list(new_files)
        _logger.info("----> new files: " + str(new_files))
        json_files = []
        cmp_log = self.env['cmp.message.log']
        message_log = ''
        if new_files:
            for i in new_files:
                lstatout=str(ftp_client.lstat(i)).split()[0]
                _logger.info("----> lstatout: " + str(lstatout))
                if 'd' not in lstatout:
                    f_name = i
                    _logger.info("----> " + str(f_name) + " is a file")
                    if not 'DONE_ODOO_' in f_name:
                        _logger.info("----> " + str(f_name) + " doesn't have DONE_ODOO_")
                        json_files.append(f_name)
                        ftp_client.get(str(f_name), local_path + "/" + str(f_name))
                        renamed_file = "DONE_ODOO_" + f_name
                        old_path = remote_path + '/' + f_name
                        new_path = remote_path + '/' + renamed_file
                        ftp_client.rename(old_path, new_path)

            base_path = os.path.dirname(local_path)
            files = [f for f in os.listdir(base_path)]
            decrypt_file = None
            decripted_files = []
            if len(files) > 0:
                if len(json_files) > 0:
                    errors = []
                    for file in json_files:
                        _logger.info("---> Decrypting file: " + str(file))
                        s = subprocess.getstatusoutput('gpg --batch --yes --passphrase "notsosecretpassword" -d -o ' + local_path + '/' + str(file) + ' ' + local_path + '/' + str(file))
                        _logger.info("---> subprocess: " + str(s))
                        if s[0] == 0:
                            _logger.info("---> File decrypted: " + str(file))
                            decripted_files.append(str(file))
                            file_content_binary = open(local_path + '/' + str(file), 'rb')
                            _logger.info("---> Processing file: " + str(file))
                            self.process_file(file_content_binary, o_type)
                            os.unlink(local_path + '/' + str(file))
                        else:
                            errors.append(s[1])
                            _logger.info("---> File not decrypted: " + str(file))
                            
                    if len(decripted_files) == len(json_files):
                        cmp_log.create({'log': 'Todos los ' + str(len(json_files)) + ' fueron desencriptados correctamente.'})
                    if len(errors) > 0:
                        cmp_log.create({'log': str('\n'.join(errors))})
        else:
            cmp_log.create({'log': 'No hay archivos nuevos en el directorio: ' + str(remote_path)})


    def reset_file(self, company_id, remote_path):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        _logger.info("----> before connect...")
        client.connect(hostname=company_id.cmp_host, port=company_id.cmp_port, username=company_id.cmp_user, password=company_id.cmp_password, look_for_keys=False)
        _logger.info("----> after connect...")
        ftp_client=client.open_sftp()
        directories = ftp_client.chdir(remote_path)
        _logger.info("listdir: " + str(ftp_client.listdir()))
        json_files = []
        for i in ftp_client.listdir():
            lstatout=str(ftp_client.lstat(i)).split()[0]
            if 'd' not in lstatout:
                f_name = i
                _logger.info(str(f_name) + " is a file")
                json_files.append(f_name)
                string_to_remove = "DONE_ODOO_"
                if "DONE_ODOO_" in f_name:
                    renamed_file = f_name.replace(string_to_remove, "")
                    old_path = remote_path + '/' + f_name
                    new_path = remote_path + '/' + renamed_file
                    ftp_client.rename(old_path, new_path)
        
        message = "Yeah, files were renamed successfully."
        return {
                        'effect': {
                        'fadeout': 'fast',
                        'message': message,
                        'img_url': 'itl_cmp_interface/static/src/img/images_1.jpeg',
                        'type': 'rainbow_man',
                        }
                    }

    def process_file(self, file, o_type):
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        file_content = file.read()
        file_b64 = base64.b64encode(file_content)
        file_name = os.path.basename(file.name)
        file_type = str(company_id.cmp_recurringprepaymentsextract_local_path).split('/')[-1]
        _logger.info("----> file_type: " + str(file_type))
        vals = {
                'file': file_b64,
                'file_name': file_name,
                'company_id': company_id.id
            }
        cmp_message = self.env['cmp.message']
        cmp_m = cmp_message.create(vals)
        if o_type == 'recurring':
            try:
                file_content_json = json.loads(file_content)
                _logger.info("----> file_content_json: " + str(file_content_json))
                msg_id = file_content_json['id']
                message = cmp_message.search([('message_id','=',msg_id)])
                if not message:
                    job_code = file_content_json['jobCode']
                    job_description = file_content_json['jobDescription']
                    batch_date_time = file_content_json['batchDateTime']

                    new_vals = {
                        'name': o_type,
                        'message_id': msg_id,
                        'content_file': file_content_json,
                        'job_code': job_code,
                        'job_description': job_description,
                        'batch_date_time': batch_date_time
                    }

                    cmp_m.write(new_vals)
                    #cmp_m.name = file_type
                    #cmp_m.message_id = msg_id
                    #cmp_m.content_file = file_content_json
                    #cmp_m.job_code = job_code
                    #cmp_m.job_description = job_description
                    #cmp_m.batch_date_time = datetime.strptime(batch_date_time, '%Y-%m-%dT%H:%M:%S.%f').strftime("%Y-%m-%dT%H:%M:%S")

                    details = file_content_json['details']
                    item_list = []
                    for detail in details:
                        cmp_item = self.env['cmp.item']
                        item_vals = {}

                        if 'transactionNumber' in detail:
                            item_vals.update(transaction_number = detail['transactionNumber'])
                        if 'paymentType' in detail:
                            item_vals.update(payment_type = detail['paymentType'])
                        if 'accountNumber' in detail:
                            item_vals.update(account_number = detail['accountNumber'])
                        if 'amount' in detail:
                            item_vals.update(amount = detail['amount'])
                        if 'nameOnCard' in detail:
                            item_vals.update(name_on_card = detail['nameOnCard'])
                        if 'cardNumber' in detail:
                            item_vals.update(card_number = detail['cardNumber'])
                        if 'startDateYymm' in detail:
                            item_vals.update(start_date = detail['startDateYymm'])
                        if 'endDateYymm' in detail:
                            item_vals.update(end_date = detail['endDateYymm'])
                        if 'cardReferenceNumber' in detail:
                            item_vals.update(card_reference_number = detail['cardReferenceNumber'])
                        if 'cardType' in detail:
                            item_vals.update(card_type = detail['cardType'])

                        _logger.info("---> len(detail['cardReferenceNumber']): " + str(len(detail['cardReferenceNumber'])))
                        _logger.info("---> detail['cardReferenceNumber']: " + str(detail['cardReferenceNumber']))
                        if len(detail['cardReferenceNumber']) == 15:
                            item_vals.update(token_type = 'amex')
                        else:
                            item_vals.update(token_type = 'visa_mastercard')

                        item_list.append((0, 0, item_vals))

                    if len(item_list) > 0:
                        cmp_m.cmp_item_ids = item_list
                    #cmp_m = cmp_message.create(vals)
                else:
                    cmp_m.message_post(body="Advertencia: El archivo ya fue procesado con anterioridad.", subject="Registro no procesado")
                    return False
            except Exception as e:
                _logger.info("Error log: " + str(e))
                cmp_m.status = 'error'
                cmp_m.message_post(body="Advertencia: Error al procesar el archivo. Error: " + str(e), subject="Registro no procesado")
                return e

            cmp_m.with_context(force_company=sr_company_id).process_details()
            return False

        if o_type == 'receipt':
            cmp_message = self.env['cmp.receipt.print.extract']
            vals = {
                'name': file_type,
                'content_file': file_content,
                'file': file_b64,
                'file_name': file_name
            }
            cmp_message.create(vals)
            _logger.info("---> Receipt created")
        
        if o_type == 'datawarehouse':
            cmp_message = self.env['cmp.datawarehouse.extract']
            vals = {
                'name': file_type,
                'content_file': file_content,
                'file': file_b64,
                'file_name': file_name
            }
            cmp_message.create(vals)
            _logger.info("---> Datawarehouse created")

