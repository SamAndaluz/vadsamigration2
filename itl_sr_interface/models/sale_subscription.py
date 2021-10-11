from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    partner_id_ref = fields.Char(string='Partner Ref')
    account_id_ref = fields.Char(string='CMP account number')
    subscription_id_ref = fields.Char(string="CMP subscription number")
    iccid_number = fields.Char(string="ICCID number")
    msisdn_number = fields.Char(string="MSISDN number")
    order_ref_id = fields.Char(string="Order Ref Id")


    # Inherit from sale_subscription.sale_subscription
    def partial_invoice_line(self, sale_order, option_line, refund=False, date_from=False):
        """ Add an invoice line on the sales order for the specified option and add a discount
        to take the partial recurring period into account """
        order_line_obj = self.env['sale.order.line']
        ratio, message = self._partial_recurring_invoice_ratio(date_from=date_from)
        if message != "":
            sale_order.message_post(body=message)
        _discount = (1 - ratio) * 100
        values = {
            'order_id': sale_order.id,
            'product_id': option_line.product_id.id,
            'subscription_id': self.id,
            'product_uom_qty': option_line.quantity,
            'product_uom': option_line.uom_id.id,
            'discount': _discount,
            'price_unit': self.pricelist_id.with_context({'uom': option_line.uom_id.id}).get_product_price(option_line.product_id, 1, False),
            'name': option_line.name,
        }
        # Custom
        context = self._context
        #_logger.info("-> Context: " + str(context))
        if 'price_unit' in context:
            #_logger.info("-> Entró en el context")
            price_unit = context.get('price_unit')
            values.update({'price_unit': price_unit})
            
        if 'discount' in context:
            discount = context.get('discount')
            values.update({'discount': discount})

        return order_line_obj.create(values)

    # Inherit from sale_subscription.sale_subscription
    def _prepare_invoice_line(self, line, fiscal_position):
        if 'force_company' in self.env.context:
            company = self.env['res.company'].browse(self.env.context['force_company'])
        else:
            company = line.analytic_account_id.company_id
            line = line.with_context(force_company=company.id, company_id=company.id)

        account = line.product_id.property_account_income_id
        if not account:
            account = line.product_id.categ_id.property_account_income_categ_id
        account_id = fiscal_position.map_account(account).id

        tax = line.product_id.taxes_id.filtered(lambda r: r.company_id == company)
        tax = fiscal_position.map_tax(tax, product=line.product_id, partner=self.partner_id)

        price_unit = 0.0
        context = self._context
        if 'price_unit' in context:
            _logger.info("-> Entró en el context")
            price_unit = context.get('price_unit')
        else:
            price_unit = line.price_unit or 0.0

        return {
            'name': line.name,
            'account_id': account_id,
            'account_analytic_id': line.analytic_account_id.analytic_account_id.id,
            'subscription_id': line.analytic_account_id.id,
            'price_unit': price_unit,
            'discount': line.discount,
            'quantity': line.quantity,
            'uom_id': line.uom_id.id,
            'product_id': line.product_id.id,
            'invoice_line_tax_ids': [(6, 0, tax.ids)],
            'analytic_tag_ids': [(6, 0, line.analytic_account_id.tag_ids.ids)]
        }

    # Inherit from sale_subscription.sale_subscription
    def _prepare_invoice_lines(self, fiscal_position):
        self.ensure_one()
        fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position)
        # Se agregó filtro para colocar solo los productos que son plan
        #return [(0, 0, self._prepare_invoice_line(line, fiscal_position)) for line in self.recurring_invoice_line_ids]
        product_plan = self.recurring_invoice_line_ids.filtered(lambda line: line.product_id.isRecurring or 'Recurrente' in line.product_id.name)
        if len(product_plan) != 0:
            product_plan = product_plan[-1]
            return [(0, 0, self._prepare_invoice_line(product_plan, fiscal_position))]

class SaleSubscriptionWizard(models.TransientModel):
    _inherit = 'sale.subscription.wizard'

    @api.multi
    def itl_create_sale_order(self):
        fpos_id = self.env['account.fiscal.position'].get_fiscal_position(self.subscription_id.partner_id.id)
        sale_order_obj = self.env['sale.order']
        #team = self.env['crm.team']._get_default_team_id(user_id=self.subscription_id.user_id.id)
        param = self.env['ir.config_parameter'].sudo()
        sr_company_id = param.get_param('itl_sr_interface.sr_company_id')
        company_id = self.env['res.company'].search([('id','=',sr_company_id)])[0]
        sr_warehouse_id = company_id.sr_warehouse_id
        new_order_vals = {
            'partner_id': self.subscription_id.partner_id.id,
            'analytic_account_id': self.subscription_id.analytic_account_id.id,
            'team_id': False,
            'pricelist_id': self.subscription_id.pricelist_id.id,
            'fiscal_position_id': fpos_id,
            'subscription_management': 'upsell',
            'origin': self.subscription_id.code,
            'company_id': company_id.id
        }

        if sr_warehouse_id:
            new_order_vals.update({'warehouse_id': sr_warehouse_id.id})
            if sr_warehouse_id.operating_unit_id:
                new_order_vals.update({'operating_unit_id': sr_warehouse_id.operating_unit_id.id})

        # we don't override the default if no payment terms has been set on the customer
        if self.subscription_id.partner_id.property_payment_term_id:
            new_order_vals['payment_term_id'] = self.subscription_id.partner_id.property_payment_term_id.id
        order = sale_order_obj.create(new_order_vals)
        for line in self.option_lines:
            self.subscription_id.partial_invoice_line(order, line, date_from=self.date_from)
        order.order_line._compute_tax_id()
        return order