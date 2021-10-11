from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class ElavonSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    elavon_hostname = fields.Char(string="Hostname", required=True)
    elavon_port = fields.Char(string="Port", required=True)
    elavon_user = fields.Char(string="User", required=True)
    elavon_password = fields.Char(string="Password", required=True)
    elavon_id_buzon = fields.Char(string="Inbox/Outbox identifier", required=True)
    elavon_id_company = fields.Char(string="Company identifier", required=True)
    elavon_local_inbox_path = fields.Char(string="Local inbox path", required=True)
    elavon_local_outbox_path = fields.Char(string="Local outbox path", required=True)
    elavon_remote_inbox_path = fields.Char(string="Remote inbox path", required=True)
    elavon_remote_outbox_path = fields.Char(string="Remote outbox path", required=True)

    def set_values(self):
        res = super(ElavonSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        
        elavon_hostname = self.elavon_hostname or False
        elavon_port = self.elavon_port or False
        elavon_user = self.elavon_user or False
        elavon_password = self.elavon_password or False
        elavon_id_buzon = self.elavon_id_buzon or False
        elavon_id_company = self.elavon_id_company or False
        elavon_local_inbox_path = self.elavon_local_inbox_path or False
        elavon_local_outbox_path = self.elavon_local_outbox_path or False
        elavon_remote_inbox_path = self.elavon_remote_inbox_path or False
        elavon_remote_outbox_path = self.elavon_remote_outbox_path or False
        
        param.set_param('itl_elavon_cron.elavon_hostname', elavon_hostname)
        param.set_param('itl_elavon_cron.elavon_port', elavon_port)
        param.set_param('itl_elavon_cron.elavon_user', elavon_user)
        param.set_param('itl_elavon_cron.elavon_password', elavon_password)
        param.set_param('itl_elavon_cron.elavon_id_buzon', elavon_id_buzon)
        param.set_param('itl_elavon_cron.elavon_id_company', elavon_id_company)
        param.set_param('itl_elavon_cron.elavon_local_inbox_path', elavon_local_inbox_path)
        param.set_param('itl_elavon_cron.elavon_local_outbox_path', elavon_local_outbox_path)
        param.set_param('itl_elavon_cron.elavon_remote_inbox_path', elavon_remote_inbox_path)
        param.set_param('itl_elavon_cron.elavon_remote_outbox_path', elavon_remote_outbox_path)
        
        return res
    
    @api.model
    def get_values(self):
        res = super(ElavonSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        elavon_hostname = ICPSudo.get_param('itl_elavon_cron.elavon_hostname')
        elavon_port = ICPSudo.get_param('itl_elavon_cron.elavon_port')
        elavon_user = ICPSudo.get_param('itl_elavon_cron.elavon_user')
        elavon_password = ICPSudo.get_param('itl_elavon_cron.elavon_password')
        elavon_id_buzon = ICPSudo.get_param('itl_elavon_cron.elavon_id_buzon')
        elavon_id_company = ICPSudo.get_param('itl_elavon_cron.elavon_id_company')
        elavon_local_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_inbox_path')
        elavon_local_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_local_outbox_path')
        elavon_remote_inbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_inbox_path')
        elavon_remote_outbox_path = ICPSudo.get_param('itl_elavon_cron.elavon_remote_outbox_path')
        
        res.update(
            elavon_hostname=elavon_hostname,
            elavon_port=elavon_port,
            elavon_user=elavon_user,
            elavon_password=elavon_password,
            elavon_id_buzon=elavon_id_buzon,
            elavon_id_company=elavon_id_company,
            elavon_local_inbox_path=elavon_local_inbox_path,
            elavon_local_outbox_path=elavon_local_outbox_path,
            elavon_remote_inbox_path=elavon_remote_inbox_path,
            elavon_remote_outbox_path=elavon_remote_outbox_path
        )
        
        return res

    def test_upload(self):
        account = self.env['account.invoice'].check_open_invoices()

        context = dict(self.env.context or {})
        return {
                'name': _('Response:'),
                'view_type': 'form',
                'res_model': 'do.place.order.event',
                'view_id': False,
                'views': [(self.env.ref('abs_sr_api.view_do_place_order_event_form').id, 'form')],
                'type': 'ir.actions.act_window',
                'context': context,
                'target' : 'new',
                }
    
    def test_download(self):
        account = self.env['account.invoice'].check_server_outbox()

        context = dict(self.env.context or {})
        return {
                'name': _('Response:'),
                'view_type': 'form',
                'res_model': 'do.place.order.event',
                'view_id': False,
                'views': [(self.env.ref('abs_sr_api.view_do_place_order_event_form').id, 'form')],
                'type': 'ir.actions.act_window',
                'context': context,
                'target' : 'new',
                }