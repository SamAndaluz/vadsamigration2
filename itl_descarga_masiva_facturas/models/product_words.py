from odoo import api, exceptions, fields, models, _


class ProductWords(models.Model):
    _name = 'product.words'
    
    product_id = fields.Many2one('product.product', string="Product", required=True)
    keywords = fields.Char(string="Keywords", required=True, help="Keywords separated by '|' char. Example: Word1|Word2|Word3|Word4|...")
    #analytic_account_id = fields.Many2one('account.analytic.account', strinmg="Analityc account")
    partner_id = fields.Many2one('res.partner', string="Vendor")