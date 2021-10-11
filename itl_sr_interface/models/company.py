from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    
    sr_host = fields.Char(string="Host")
    sr_port = fields.Char(string="Port")
    sr_key_path = fields.Char(string="Key path")
    sr_password = fields.Char(string="Password")
    sr_queue = fields.Char(string="Subscription queue")
    sr_response_queue = fields.Char(string="Subscription response queue")

    sr_sim_product_id = fields.Many2one('product.template', string="SIM Product")
    sr_rokit_product_id = fields.Many2one('product.template', string="ROKiT Product")
    sr_tax_id = fields.Many2one('account.tax', string="Tax to add to subscription product")
    sr_warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse for SO")
    sr_carrier_id = fields.Many2one('delivery.carrier', string="Delivery carrier SO")
    sr_payment_journal_id = fields.Many2one('account.journal', string="Journal for payment invoice", domain=[('type', 'in', ('bank', 'cash'))])
    sr_activation_legacy_product_name = fields.Char(string="Activation Legacy Product Name", readonly=False)