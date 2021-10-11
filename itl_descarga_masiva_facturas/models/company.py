from odoo import api, fields, models
# from odoo.addons.l10n_mx_edi.hooks import _load_xsd_files


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    pfx_file = fields.Binary(string="Archivo PFX", help="Archivo generado con la FIEL del contribuyente")
    filename = fields.Char(string='Nombre archivo')
    password_pfx = fields.Char(string="Contraseña del archivo .pfx")
    contrato = fields.Char(string="Contrato", help="Indica el código de contrato del usuario con el que se realizará la solicitud")
    
    active_cliente = fields.Boolean(string="Descargar facturas cliente", default=False)
    active_proveedor = fields.Boolean(string="Descargar facturas proveedor", default=False)
    
    # Configuración facturas cliente
    cuenta_cobrar_cliente_id = fields.Many2one('account.account', string='Cuenta por Cobrar Clientes')
    invoice_status_customer = fields.Selection([('draft', 'Borrador'), ('abierta', 'Abierta'), ('pagada', 'Pagada')],string='Subir en estatus')
    user_customer_id = fields.Many2one('res.users', string='Representante Comercial')
    team_customer_id = fields.Many2one('crm.team', string='Equipo de ventas')
    journal_customer_id = fields.Many2one('account.journal', string='Diario Clientes')
    cuenta_ingreso_cliente_id = fields.Many2one('account.account',
                                                string='Cuenta de Ingresos Clientes',
                                                required=False, default=lambda self: self.env['account.account'].search(
            [('code', '=', '401.01.001'), ('company_id', '=', self.env.user.company_id.id)]))
    
    # Configuración facturas proveedor
    cuenta_pagar_proveedor_id = fields.Many2one('account.account', string='Cuenta por Pagar Proveedores')
    invoice_status_provider = fields.Selection([('draft', 'Borrador'), ('abierta', 'Abierta'), ('pagada', 'Pagada')], string='Subir en estatus', required=False)
    warehouse_provider_id = fields.Many2one('stock.warehouse', string='Almacén', help='Necesario para crear el mov. de almacén')
    journal_provider_id = fields.Many2one('account.journal', string='Diario Proveedores')
    user_provider_id = fields.Many2one('res.users', string='Comprador')
    cuenta_gasto_proveedor_id = fields.Many2one('account.account',
                                                string='Cuenta de Gastos de Proveedor',
                                                default=lambda self: self.env['account.account'].search(
            [('code', '=', '601.84.001'), ('company_id', '=', self.env.user.company_id.id)]))
    
    xml_import_line_ids = fields.One2many('res.company.xml.import.line',
                                    'company_id',
                                    string='Configuracion de importacion de xmls')
    
class ResCompanyXmlImportLine(models.Model):
    _name = 'res.company.xml.import.line'


    company_id = fields.Many2one('res.company', string='Compañia',required=True,)
    xml_import_analytic_account_id = fields.Many2one('account.analytic.account',
        string='Cuenta analitica',
        required=True,
        help='Esta cuenta analitica se utilizara pra las facturas improtadas con el importador de xmls')
    xml_import_warehouse_id = fields.Many2one('stock.warehouse',
        string='Almacen',
        required=True,
        help='Este almacen se utilizara para hacer los movimientos de inventario ' + \
        'que se generen en las facturas improtadas con el modulo de importacion de xmls')
    xml_import_journal_id = fields.Many2one('account.journal',
        string='Diario',
        required=True,
        help='Este diario se utlizara en las facturas importadas con el importador de xmls')
    xml_import_bank_id = fields.Many2one('account.journal',
        string='Banco',
        required=True,
        domain="[('type','=','bank')]",
        help='Este banco se utlizara en las facturas importadas con el importador de xmls')