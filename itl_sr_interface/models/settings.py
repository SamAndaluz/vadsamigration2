from odoo import models, fields, api


class AbsSrConfi(models.TransientModel):
    _inherit = 'res.config.settings'
    

    sr_host = fields.Char(related="company_id.sr_host", string="Host", readonly=False)
    sr_port = fields.Char(related="company_id.sr_port", string="Port", readonly=False)
    sr_key_path = fields.Char(related="company_id.sr_key_path", string="Key path", readonly=False)
    sr_password = fields.Char(related="company_id.sr_password", string="Password", readonly=False)
    sr_queue = fields.Char(related="company_id.sr_queue", string="Subscription queue", readonly=False)
    sr_response_queue = fields.Char(related="company_id.sr_response_queue", string="Subscription response queue", readonly=False)

    sr_sim_product_id = fields.Many2one('product.template', related="company_id.sr_sim_product_id", string="SIM Product", readonly=False)
    sr_rokit_product_id = fields.Many2one('product.template', related="company_id.sr_rokit_product_id", string="ROKiT Product", readonly=False)
    sr_warehouse_id = fields.Many2one('stock.warehouse', related="company_id.sr_warehouse_id", string="Warehouse for SO", readonly=False)
    sr_carrier_id = fields.Many2one('delivery.carrier', related="company_id.sr_carrier_id", string="Delivery carrier SO", readonly=False)
    sr_tax_id = fields.Many2one('account.tax', related="company_id.sr_tax_id", string="Tax to add to subscription product", readonly=False)
    sr_payment_journal_id = fields.Many2one('account.journal', related="company_id.sr_payment_journal_id", string="Journal", readonly=False)
    sr_activation_legacy_product_name = fields.Char(related="company_id.sr_activation_legacy_product_name", string="Activation Legacy Product Name", readonly=False)

    sr_company_id = fields.Many2one('res.company', string="Default company", readonly=False)

    @api.model
    def get_values(self):
        res = super(AbsSrConfi, self).get_values()
        res.update(
            sr_company_id = int(self.env['ir.config_parameter'].sudo().get_param('itl_sr_interface.sr_company_id'))
        )
        return res

    @api.multi
    def set_values(self):
        super(AbsSrConfi, self).set_values()
        param = self.env['ir.config_parameter'].sudo()

        sr_company_id = self.sr_company_id and self.sr_company_id.id or False

        param.set_param('itl_sr_interface.sr_company_id', sr_company_id)