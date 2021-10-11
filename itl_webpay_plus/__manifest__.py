# -*- coding: utf-8 -*-
{
    'name': "ITL WebPay Plus",

    'summary': """
        Este módulo permite generar un link de pago con WebPay Plus y recibir la 
        notificación de cobro para después pagar la factura en odoo.""",

    'description': """
        Este módulo permite generar un link de pago con WebPay Plus y recibir la 
        notificación de cobro para después pagar la factura en odoo.
    """,

    'author': "ITLighten",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','payment','website_sale','mail'],

    # always loaded
    'data': [
        'data/payment_acquirer_data.xml',
        'views/payment_views.xml',
        'views/account_invoice_views.xml',
        'views/res_partner_view.xml',
        'security/ir.model.access.csv'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}