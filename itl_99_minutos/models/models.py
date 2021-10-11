# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json
import requests
from odoo.exceptions import UserError, ValidationError

class itl_99_minutos_order(models.Model):
	_name = "itl.99.minutos.order"

	def _get_default_company(self):
		param = self.env['ir.config_parameter'].sudo()
		sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
		company_id = False
		if sr_company_id:
			company_id = self.env['res.company'].browse(int(sr_company_id))
			
		return company_id


	operation_type = fields.Selection([('create_order','Crear orden'),
										('status_order','Consultar orden'),
										('cancel_order','Cancelar orden'),
										('shipping_rate','Métodos de envío'),
										('create_guide','Crear guía')], string="Tipo de operación", readonly=True)

	url_used = fields.Char(string="URL de la petición", readonly=True)
	url_body = fields.Text(string="Cuerpo de la petición", readonly=True)
	response = fields.Text(string="Cuerpo de la respuesta", readonly=True)
	status_code = fields.Char(string="Status code", readonly=True)
	counter = fields.Char(related="stock_picking_id.carrier_counter_ref", string="Counter", readonly=True)
	trackingid = fields.Char(related="stock_picking_id.carrier_tracking_ref", string="Tracking ID", readonly=True)
	stock_picking_id = fields.Many2one('stock.picking', string="Movimiento", readonly=True)
	company_id = fields.Many2one('res.company', string="Compañía", readonly=True, store=True, default=_get_default_company)