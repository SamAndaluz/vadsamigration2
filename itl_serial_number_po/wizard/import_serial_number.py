# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ImportSerialNumber(models.TransientModel):
    _name = 'itl.import.serial.number'
    
    
    itl_file = fields.Binary(string="Seleccione un archivo")
    itl_filename = fields.Char()
    
    
    @api.onchange('itl_file')
    def _onchnage_itl_filename(self):
        if self.itl_file:
            file_ext = self.get_file_ext(self.itl_filename)
            if file_ext.lower() not in ('txt'):
                raise ValidationError('Solo se permiten archivo con extensión .txt')
            
    def get_file_ext(self, filename):
        """
        obtiene extencion de archivo, si este lo tiene
        fdevuelve false, si no cuenta con una aextension
        (no es archivo entonces)
        """
        file_ext = filename.split('.')
        if len(file_ext) > 1:
            file_ext = filename.split('.')[1]
            return file_ext
        return False
    
    def import_serial_numbers(self):
        stock_move_id = self.env['stock.move'].browse(self.env.context.get('active_id'))
        
        file_content = base64.decodestring(self.itl_file)
        file_content = file_content.decode("utf-8")
        file_lines = file_content.split("\r\n")
        
        if len(file_lines) < len(stock_move_id.move_line_ids):
            raise ValidationError("El número de líneas en el archivo es menor al número de líneas de producto.")
        if len(file_lines) > len(stock_move_id.move_line_ids):
            raise ValidationError("El número de líneas en el archivo es mayor al número de líneas de producto.")
        
        i = 0
        for ml in stock_move_id.move_line_ids:
            ml.lot_name = file_lines[i]
            ml.qty_done = ml.product_uom_qty
            i += 1
        
        return stock_move_id.action_show_details()
    