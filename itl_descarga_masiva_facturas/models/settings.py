from odoo import models, fields, api
from ast import literal_eval
import logging

_logger = logging.getLogger(__name__)

class DescargMasivaSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    url_solicitud = fields.Char(string="URL solicitud", help="URL para generar una solicitud de descarga masiva")
    url_estatus = fields.Char(string="URL estatus", help="URL para consultar el estado de la solicitud")
    
    pfx_file = fields.Binary(related="company_id.pfx_file", string="Archivo PFX", help="Archivo generado con la FIEL del contribuyente", readonly=False)
    filename = fields.Char(related="company_id.filename", string='Nombre archivo', readonly=False)
    password_pfx = fields.Char(related="company_id.password_pfx", string="Contraseña del archivo .pfx", readonly=False)
    contrato = fields.Char(related="company_id.contrato", string="Contrato", help="Indica el código de contrato del usuario con el que se realizará la solicitud", readonly=False)
    
    active_cliente = fields.Boolean(related="company_id.active_cliente", string="Descargar facturas cliente", default=False, readonly=False)
    active_proveedor = fields.Boolean(related="company_id.active_proveedor", string="Descargar facturas proveedor", default=False, readonly=False)
    
    # Configuración facturas cliente
    cuenta_cobrar_cliente_id = fields.Many2one('account.account', related="company_id.cuenta_cobrar_cliente_id", string='Cuenta por Cobrar Clientes', readonly=False)
    invoice_status_customer = fields.Selection([('draft', 'Borrador'), ('abierta', 'Abierta'), ('pagada', 'Pagada')], related="company_id.invoice_status_customer", string='Subir en estatus', readonly=False)
    user_customer_id = fields.Many2one('res.users', related="company_id.user_customer_id", string='Representante Comercial', readonly=False)
    team_customer_id = fields.Many2one('crm.team', related="company_id.team_customer_id", string='Equipo de ventas', readonly=False)
    journal_customer_id = fields.Many2one('account.journal', related="company_id.journal_customer_id", string='Diario Clientes', readonly=False)
    cuenta_ingreso_cliente_id = fields.Many2one('account.account', related="company_id.cuenta_ingreso_cliente_id", string='Cuenta de Ingresos Clientes', readonly=False)
    
    # Configuración facturas proveedor
    cuenta_pagar_proveedor_id = fields.Many2one('account.account', related="company_id.cuenta_pagar_proveedor_id", string='Cuenta por Pagar Proveedores', readonly=False)
    invoice_status_provider = fields.Selection([('draft', 'Borrador'), ('abierta', 'Abierta'), ('pagada', 'Pagada')], related="company_id.invoice_status_provider", string='Subir en estatus', required=False, readonly=False)
    warehouse_provider_id = fields.Many2one('stock.warehouse', related="company_id.warehouse_provider_id", string='Almacén', help='Necesario para crear el mov. de almacén', readonly=False)
    journal_provider_id = fields.Many2one('account.journal', related="company_id.journal_provider_id", string='Diario Proveedores', readonly=False)
    user_provider_id = fields.Many2one('res.users', related="company_id.user_provider_id", string='Comprador', readonly=False)
    cuenta_gasto_proveedor_id = fields.Many2one('account.account', related="company_id.cuenta_gasto_proveedor_id", string='Cuenta de Gastos de Proveedor', readonly=False)

    def set_values(self):
        res = super(DescargMasivaSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        
        url_solicitud = self.url_solicitud or False
        url_estatus = self.url_estatus or False
        
        param.set_param('itl_descarga_masiva.url_solicitud', url_solicitud)
        param.set_param('itl_descarga_masiva.url_estatus', url_estatus)
        
        return res
    
    @api.model
    def get_values(self):
        res = super(DescargMasivaSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        url_solicitud = ICPSudo.get_param('itl_descarga_masiva.url_solicitud')
        url_estatus = ICPSudo.get_param('itl_descarga_masiva.url_estatus')
        
        res.update(
            url_solicitud=url_solicitud,
            url_estatus=url_estatus
        )
        
        return res