from odoo import api, fields, models, _

class ProductTemplateCustom(models.Model):
    _inherit = "product.template"

    productLegacyId = fields.Char(string='Product Legacty Id', help="Identificador del producto de SR")
    productCategory = fields.Selection([('addOn','AddOn'),('plan','Plan')], string="Product Category", help="Categoría del producto de SR")
    isRecurring = fields.Boolean(string="Es recurrente", help="Indica si el Plan/AddOn es recurrente")