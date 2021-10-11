from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import io
try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'


    serial_numbers_file = fields.Binary(string="Upload file")
    serial_numbers_file_name = fields.Char("File Name")
    picking_type_code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')], related='picking_type_id.code',
        readonly=True)

    def reset_serial_number(self):
        for sml in self.move_line_ids:
            sml.lot_name = False
            sml.qty_done = 0

        return self.action_show_details()

    def load_serial_numbers(self):
        file_reader = self.get_csv_data()
        csv_len = len(file_reader) - 1

        if len(self.move_line_ids) != csv_len:

            raise ValidationError("La cantidad de números de serie en el archivo no coincide con la cantidad del producto. Total en el archivo: %s - Total de productos: %s." %(csv_len,len(self.move_line_ids)))

        self.get_values_from_csv(file_reader)
        self.serial_numbers_file = False
        self.serial_numbers_file_name = False

        return self.action_show_details()

    @api.onchange('serial_numbers_file')
    def onchnage_uploaded_file(self):
        if self.serial_numbers_file:
            file_ext = self.get_file_ext(self.serial_numbers_file_name)
            if file_ext.lower() not in ('csv'):
                raise ValidationError('Por favor, escoja un archivo .csv')

    def get_file_ext(self,filename):
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

    def get_raw_file(self):
        '''Convertir archivo binario a byte string.'''
        return base64.b64decode(self.serial_numbers_file)

    def get_txt_data(self):
        '''
            Ordena datos de archivo xml
        '''
        #xmls = []
        # convertir byte string a dict
        raw_file = self.get_raw_file()
        txt_string = raw_file.decode('utf-8')
        txt_serial_number_list = txt_string.split('\n')
        for t in txt_serial_number_list:
            _logger.info("--> text: " + str(t))
            _logger.info("--> type: " + str(type(t)))
        _logger.info("--> txt_serial_number_list: " + str(txt_serial_number_list))
        raise ValidationError("Testing...")

    def get_csv_data(self):
        csv_data = base64.b64decode(self.serial_numbers_file)
        data_file = io.StringIO(csv_data.decode("utf-8"))
        data_file.seek(0)
        file_reader = []
        csv_reader = csv.reader(data_file, delimiter=',')

        try:
            file_reader.extend(csv_reader)
            return file_reader
        except Exception:
            raise Warning(_("Invalid file!"))

    def get_values_from_csv(self, file_reader):
        lines = []
        
        for i in range(len(file_reader)):
            val = {}
            field = list(map(str, file_reader[i]))

            if field:
                if i == 0:
                    continue
                else:
                    self.move_line_ids[i-1].lot_name = field[0]
                    self.move_line_ids[i-1].qty_done = 1