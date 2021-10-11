# -*- coding: utf-8 -*-
{
    'name': "ITL OXXO payment",

    'summary': """
        Este módulo permite generar un link de pago con OXXO usando Stripe y 
        recibe la notificación de cobro para marcar la factura como pagada.""",

    'description': """
        Este módulo permite generar un link de pago con OXXO usando Stripe y 
        recibe la notificación de cobro para marcar la factura como pagada.
    """,

    'author': "ITLighten",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account','payment'],

    # always loaded
    'data': [
            #'security/ir.model.access.csv',
            'views/templates.xml',
            'views/index.xml',
            'views/oxxo_payment.xml',
            'views/account_invoice_view.xml',
            'views/payment_acquire_stripe.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}