# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'
    
    itl_tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')], related="product_id.tracking")
    
    def clear_serial_numbers(self):
        for ml in self.move_line_ids:
            ml.lot_name = False
            ml.qty_done = 0
            
        return self.action_show_details()