# -*- coding: utf-8 -*-
{
    'name': "ITL Separate Reality Interface",

    'summary': """
        Este módulo crea la lógica para leer mensajes del Active MQ de Separate Reality.""",

    'description': """
        Este módulo crea la lógica para leer mensajes del Active MQ de Separate Reality, 
        crea el cliente, el producto, la suscripción, la orden de venta y la factura ya pagada.
    """,

    'author': "ITLighten",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '14.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account','sale_subscription','product','sale','mail','stock','website_sale_delivery'],

    # always loaded
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/activemq_message_views.xml',
        'views/company_views.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/sale_subscription_views.xml',
        #'views/sale_views.xml',
        'views/settings_views.xml',
        'wizard/sr_get_message.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}