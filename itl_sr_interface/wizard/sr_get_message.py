from odoo import api, fields, models, _
from odoo.exceptions import  Warning
import time
import sys
import stomp
import logging
_logger = logging.getLogger(__name__)

class SrQueueMessage(models.TransientModel):
    _name = "sr.get.message"
    _description = "Get messages from SR ActiveMQ"


    def get_messages_from_queue(self):
        _logger.info("---------- Reading ActiveMQ Messages --------------------")
        log = self.env['sr.get.message.log']
        self._cr.autocommit(False)
        list_messages_ids = []
        list_messages_obj = []
        activemq_message = self.env['activemq.message']
        try:
            param = self.env['ir.config_parameter'].sudo()
            sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
            company_id = self.env['res.company'].browse(int(sr_company_id))

            class MyListener(stomp.ConnectionListener):
                msg_list = []

                def __init__(self):
                    self.msg_list = []
                
                def on_error(self, headers, message):
                    _logger.info('received an error "%s"' % message)
                
                def on_message(self, headers, message):
                    self.msg_list.append(message)

            prob_erros = []
            host = company_id.sr_host
            prob_erros.append(host)
            port = company_id.sr_port
            prob_erros.append(port)
            key_path = company_id.sr_key_path
            prob_erros.append(key_path)
            password = company_id.sr_password
            prob_erros.append(password)
            sr_queue = company_id.sr_queue
            prob_erros.append(sr_queue)

            if not all(prob_erros):
                log.create({'log': "Some parameters of connection are missing."})
                return False

            conn = stomp.Connection([(host, port)])
            _logger.info('---> Setting broker...')
            conn.set_ssl(for_hosts=[(host, port)], key_file=key_path, cert_file=key_path, password=password)
            _logger.info('---> Connecting...')
            conn.connect()
            _logger.info('---> Setting MyListener...')
            lst = MyListener()
            conn.set_listener('', lst)
            _logger.info('---> Subscribing to ' + str(sr_queue))
            conn.subscribe(destination=sr_queue, id=1, ack='auto')
            _logger.info('---> Successfuly subscribe...')
            time.sleep(3)
            messages = lst.msg_list
            message = "Total de mensages encontrados: " + str(len(messages)) + ", "
            _logger.info("-> " + str(message))
            i = 0
            j = 0
            for m in messages:
                _logger.info("---> XML Message: " + str(m))
                event = str(str(m).split("\n")[1])
                event = event.strip()
                event = event.replace('<','')
                event = event.replace('>','')
                event = event.strip()
                vals = {
                        'name': event,
                        'xml_message': m,
                        'status': 'new',
                        'company_id': company_id.id
                    }
                
                rec = activemq_message.sudo(self.env.user.id).create(vals)
                list_messages_obj.append(rec)
                list_messages_ids.append(rec.id)
                _logger.info("---> Message created: " + str(rec.name))
            message += "Total de mensajes tipo DoPlaceOrderEvent a procesar: " + str(i)
            message += " | "
            message += "Total de mensajes tipo DoPlaceServiceOrderEvent a procesar: " + str(j)
            log.create({'log': message, 'active_message_ids': [(6, 0, list_messages_ids)]})
            #conn.unsubscribe(1)
            conn.disconnect()
            self._cr.commit()
            _logger.info("---> Mensajes creados: " + str(len(list_messages_ids)))
            _logger.info("***> Salió de crear mensajes")
        except Exception as e:
            _logger.info("-> get_messages error: " + str(e))
            log.create({'log': str(e)})
            return

        #message_ids = activemq_message.browse(list_messages)
        for msg in list_messages_obj:
            _logger.info("---> Nuevo mensaje: " + str(msg.name))
            if 'DoPlaceOrderEvent' in msg.name:
                _logger.info("---> Entró DoPlaceOrderEvent")
                msg.do_place_order_event()
                _logger.info("---> Salió DoPlaceOrderEvent")
            if 'DoPlaceServiceOrderEvent' in msg.name:
                _logger.info("---> Entró DoPlaceServiceOrderEvent")
                msg.do_place_service_order_event()
                _logger.info("---> Salió DoPlaceServiceOrderEvent")

        _logger.info("---------- Finish Reading ActiveMQ Messages --------------------")

    def read_messages(self):
        _logger.info("---------- Reading ActiveMQ Messages --------------------")
        self._cr.autocommit(False)
        list_messages_ids = []
        list_messages_obj = []
        try:
            param = self.env['ir.config_parameter'].sudo()
            sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
            company_id = self.env['res.company'].browse(int(sr_company_id))
            log = self.env['sr.get.message.log'].with_context(force_company=sr_company_id)
            activemq_message = self.env['activemq.message'].with_context(force_company=sr_company_id)

            class MyListener(stomp.ConnectionListener):
                msg_list = []

                def __init__(self):
                    self.msg_list = []
                
                def on_error(self, headers, message):
                    _logger.info('received an error "%s"' % message)
                
                def on_message(self, headers, message):
                    self.msg_list.append(message)

            prob_erros = []
            host = company_id.sr_host
            prob_erros.append(host)
            port = company_id.sr_port
            prob_erros.append(port)
            key_path = company_id.sr_key_path
            prob_erros.append(key_path)
            password = company_id.sr_password
            prob_erros.append(password)
            sr_queue = company_id.sr_queue
            prob_erros.append(sr_queue)

            if not all(prob_erros):
                log.create({'log': "Some parameters of connection are missing."})
                return False

            conn = stomp.Connection([(host, port)])
            _logger.info('---> Setting broker...')
            conn.set_ssl(for_hosts=[(host, port)], key_file=key_path, cert_file=key_path, password=password)
            _logger.info('---> Connecting...')
            conn.connect()
            _logger.info('---> Setting MyListener...')
            lst = MyListener()
            conn.set_listener('', lst)
            _logger.info('---> Subscribing to ' + str(sr_queue))
            conn.subscribe(destination=sr_queue, id=1, ack='auto')
            _logger.info('---> Successfuly subscribe...')
            time.sleep(3)
            messages = lst.msg_list
            message = "Total de mensages encontrados: " + str(len(messages)) + ", "
            _logger.info("-> " + str(message))
            i = 0
            j = 0
            for m in messages:
                _logger.info("---> XML Message: " + str(m))
                event = str(str(m).split("\n")[1])
                event = event.strip()
                event = event.replace('<','')
                event = event.replace('>','')
                event = event.strip()
                vals = {
                        'name': event,
                        'xml_message': m,
                        'status': 'new',
                        'company_id': company_id.id
                    }
                
                rec = activemq_message.sudo().create(vals)
                list_messages_obj.append(rec)
                list_messages_ids.append(rec.id)
                _logger.info("---> Message created: " + str(rec.name))
            message += "Total de mensajes tipo DoPlaceOrderEvent a procesar: " + str(i)
            message += " | "
            message += "Total de mensajes tipo DoPlaceServiceOrderEvent a procesar: " + str(j)
            log.create({'log': message, 'active_message_ids': [(6, 0, list_messages_ids)]})
            #conn.unsubscribe(1)
            conn.disconnect()
            self._cr.commit()
            _logger.info("---> Mensajes creados: " + str(len(list_messages_ids)))
            _logger.info("***> Salió de crear mensajes")
        except Exception as e:
            _logger.info("-> get_messages error: " + str(e))
            log.create({'log': str(e)})
            return

        _logger.info("---------- Finish Reading ActiveMQ Messages --------------------")

    def process_messages(self):
        _logger.info("------------------ Processing messages ---------")
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        _logger.info("---> sr_company_id: " + str(sr_company_id))
        activemq_message = self.env['activemq.message']
        company_id = self.env['res.company'].browse(int(sr_company_id))
        list_messages_obj = activemq_message.sudo().search([('status','=','new'),('company_id','=',company_id.id)])
        _logger.info("---> Total messages to process: " + str(len(list_messages_obj)))
        for msg in list_messages_obj:
            if 'DoPlaceOrderEvent' in msg.name:
                _logger.info("#####> Entró DoPlaceOrderEvent")
                msg.with_context(force_company=sr_company_id).sudo().do_place_order_event()
                _logger.info("#####> Salió DoPlaceOrderEvent")
            if 'DoPlaceServiceOrderEvent' in msg.name:
                _logger.info("*****> Entró DoPlaceServiceOrderEvent")
                msg.with_context(force_company=sr_company_id).sudo().do_place_service_order_event()
                _logger.info("*****> Salió DoPlaceServiceOrderEvent")

        _logger.info("------------------ Finish processing messages ---------")

    def send_message_to_queue(self, mensaje):
        try:
            param = self.env['ir.config_parameter'].sudo()
            sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
            company_id = self.env['res.company'].browse(int(sr_company_id))
            prob_erros = []
            host = company_id.sr_host
            prob_erros.append(host)
            port = company_id.sr_port
            prob_erros.append(port)
            key_path = company_id.sr_key_path
            prob_erros.append(key_path)
            password = company_id.sr_password
            prob_erros.append(password)
            sr_response_queue = company_id.sr_response_queue
            prob_erros.append(sr_response_queue)

            if not all(prob_erros):
                return False

            conn = stomp.Connection([(host, port)])
            _logger.info('Setting broker...')
            conn.set_ssl(for_hosts=[(host, port)], key_file=key_path, cert_file=key_path, password=password)
            _logger.info('Connecting...')
            conn.connect()
            _logger.info('Sending message to queue: ' + str(sr_response_queue))
            conn.send(sr_response_queue, mensaje)
            _logger.info('Disconnecting...')
            conn.disconnect()

            return True
        except Exception as e:
            _logger.info("-> send_message_to_queue error: " + str(e))
            return False


class SrQueueMessageLog(models.Model):
    _name = "sr.get.message.log"
    _description = "SR ActiveMQ message log"
    _rec_name = "id"

    log = fields.Text(readonly=True)
    active_message_ids = fields.Many2many('activemq.message', 'log_id', string="Messages", readonly=True)

    